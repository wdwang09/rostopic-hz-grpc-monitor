import threading
import time
from typing import List, Dict

import pandas as pd
import grpc

import rostopic_hz_pb2
import rostopic_hz_pb2_grpc

# =============================================
# =============================================
# =============================================
# =============================================
port = 60480
ip_list = ["localhost"]
topic_list = [
    "/camera/imu",
    "/camera/odom/sample",
    "/d400/imu",
    "/d400/aligned_depth_to_color/image_raw",
]
# =============================================
# =============================================
# =============================================
# =============================================

hz_last_time_dict: Dict[str, float] = dict()
hz_dict: Dict[str, Dict[str, float]] = dict()


def run(ip: str, port: str, topics: List[str]) -> None:
    # if ip not in hz_dict:
    #     hz_dict[ip] = {}
    ip_port = f"{ip}:{port}"
    with grpc.insecure_channel(ip_port) as channel:
        stub = rostopic_hz_pb2_grpc.RostopicHzRpcStub(channel)
        stub.stopMonitor(rostopic_hz_pb2.Empty())
        topics_msg = rostopic_hz_pb2.Topics()
        for topic in topics:
            topics_msg.topics.append(topic)
        stub.addTopics(topics_msg)
        responses = stub.joinClient(rostopic_hz_pb2.Empty())
        for res in responses:
            hz_last_time_dict[ip] = time.time()
            hz_dict[ip] = {}
            for topic, hz in zip(res.topics, res.hzs):
                hz_dict[ip][topic] = f"{hz:.2f}"


if __name__ == "__main__":
    print("===== Config =====")
    print("IP and port", ip_list, port)
    print("Topics", topic_list)
    print("==================")
    for ip in ip_list:
        threading.Thread(target=run, args=(ip, port, topic_list), daemon=True).start()
    while True:
        curr_time = time.time()
        for ip in hz_last_time_dict:
            if curr_time - hz_last_time_dict[ip] > 2:
                hz_dict[ip] = {}
        # print(hz_dict)
        print("===================================================")
        print(pd.DataFrame.from_dict(hz_dict))
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
