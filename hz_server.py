import multiprocessing as mp
import time
import threading
from concurrent import futures
from typing import Dict, List

import grpc
import rospy
from std_msgs.msg import String

import rostopic_hz_pb2
import rostopic_hz_pb2_grpc

from rostopic_hz_monitor import RostopicHzMonitor


class MyRostopicHzRpcServicer(rostopic_hz_pb2_grpc.RostopicHzRpcServicer):
    def __init__(self):
        rospy.init_node("my_hz", anonymous=True)
        self.monitor = RostopicHzMonitor()
        self.hz_sub = rospy.Subscriber(
            "/rostopic_monitor_hz", String, self.__hz_callback
        )
        self.last_hz_received = ""
        self.last_hz_time_received = 0

    def __hz_string_to_grpc(self) -> rostopic_hz_pb2.RostopicHzResponse:
        response = rostopic_hz_pb2.RostopicHzResponse()
        pairs = self.last_hz_received.split("|")
        for i in range(len(pairs) // 2):
            response.topics.append(pairs[2 * i])
            response.hzs.append(eval(pairs[2 * i + 1]))
        return response

    def __hz_callback(self, msg: String):
        self.last_hz_received = msg.data
        self.last_hz_time_received = time.time()

    def joinClient(
        self, request: rostopic_hz_pb2.Empty, context: grpc.ServicerContext
    ) -> rostopic_hz_pb2.RostopicHzResponse:
        def cancel():
            self.monitor.stop()
            return

        context.add_callback(cancel)
        while True:
            if time.time() - self.last_hz_time_received >= 2:
                self.last_hz_received = ""
            # print(time.time())
            # print(self.__hz_string_to_grpc())
            yield self.__hz_string_to_grpc()
            time.sleep(1)

    def addTopics(
        self, request: rostopic_hz_pb2.Topics, context: grpc.ServicerContext
    ) -> rostopic_hz_pb2.Successes:
        response = rostopic_hz_pb2.Successes()
        for topic in request.topics:
            if topic in self.monitor.topic_subs:
                response.successes.append(True)
            else:
                response.successes.append(self.monitor.add_topic(topic))
        # print(response.successes)
        return response

    def removeTopics(
        self, request: rostopic_hz_pb2.Topics, context: grpc.ServicerContext
    ) -> rostopic_hz_pb2.Empty:
        response = rostopic_hz_pb2.Empty()
        for topic in request.topics:
            self.monitor.remove_topic(topic)
        return response

    def stopMonitor(
        self, request: rostopic_hz_pb2.Empty, context: grpc.ServicerContext
    ) -> rostopic_hz_pb2.Empty:
        self.monitor.stop()
        response = rostopic_hz_pb2.Empty()
        return response


def serve(ip):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=3))
    rostopic_hz_pb2_grpc.add_RostopicHzRpcServicer_to_server(
        MyRostopicHzRpcServicer(), server
    )
    server.add_insecure_port(f"[::]:{ip}")
    server.start()
    p = threading.Thread(target=server.wait_for_termination, daemon=True)
    p.start()


if __name__ == "__main__":
    serve(60480)
    rospy.spin()
