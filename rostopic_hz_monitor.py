#!/usr/bin/env python3
import re
import multiprocessing as mp
import threading
from typing import Dict, List

# from queue import Queue
from collections import deque

import rospy
from std_msgs.msg import String


class RostopicHzMonitor:
    def __init__(self, max_sec=3):
        self.topic_subs: Dict[str, rospy.Subscriber] = dict()
        self.topic_times: Dict[str, deque] = dict()
        self.max_sec = max_sec
        self.hz_pub = rospy.Publisher("/rostopic_monitor_hz", String, queue_size=3)
        rospy.Timer(rospy.Duration(1), self.hz_timer)
        # self.is_working = False
        self.lock = threading.Lock()

    # def start(self):
    #     self.is_working = True

    def stop(self):
        # self.is_working = False
        topics = list(self.topic_subs.keys())
        for topic in topics:
            self.remove_topic(topic)

    def add_topic(self, topic_name: str):
        # http://wiki.ros.org/Names#Valid_Names
        # https://docs.python.org/3/library/re.html
        valid_regex = re.compile("[a-zA-Z~/][a-zA-Z0-9_/]*")
        if valid_regex.fullmatch(topic_name) is None:
            rospy.logerr(f'"{topic_name}" is not a valid ROS topic name.')
            return False
        if topic_name in self.topic_subs:
            rospy.logerr(f'"{topic_name}" has been monitored.')
            return False
        # if not self.is_working:
        #     return
        self.topic_subs[topic_name] = rospy.Subscriber(
            topic_name, rospy.AnyMsg, self.__hz_callback, callback_args=topic_name
        )
        self.topic_times[topic_name] = deque()
        return True

    def remove_topic(self, topic_name: str):
        self.lock.acquire()
        if topic_name in self.topic_subs:
            self.topic_subs[topic_name].unregister()
            self.topic_subs.pop(topic_name)
        if topic_name in self.topic_times:
            self.topic_times.pop(topic_name)
        self.lock.release()

    def __hz_callback(self, data: rospy.AnyMsg, topic_name: str):
        curr_time = rospy.get_time()
        # if topic_name not in self.topic_subs:
        #     self.topic_times[topic_name] = deque()
        self.topic_times[topic_name].append(curr_time)
        while curr_time - self.topic_times[topic_name][0] > self.max_sec:
            self.topic_times[topic_name].popleft()

    # How many messages in 5 seconds?
    def calculate_hz(self) -> Dict[str, float]:
        # print(list(self.topic_times.keys()))
        topic_hz: Dict[str, float] = dict()
        curr_time = rospy.get_time()
        for topic_name in self.topic_times:
            while (
                len(self.topic_times[topic_name]) != 0
                and curr_time - self.topic_times[topic_name][0] > self.max_sec
            ):
                self.topic_times[topic_name].popleft()
            msg_num = len(self.topic_times[topic_name])
            hz = 0
            if msg_num == 0:
                hz = 0
            else:
                hz = msg_num / (curr_time - self.topic_times[topic_name][0])
            topic_hz[topic_name] = hz
        return topic_hz

    def hz_timer(self, event):
        # if not self.is_working:
        #     return
        hz_dict = self.calculate_hz()

        msg = String()
        for topic in hz_dict:
            hz = hz_dict[topic]
            msg.data += topic
            msg.data += "|"
            msg.data += (
                str(hz) if type(hz) != float else "{:.2f}".format(hz_dict[topic])
            )
            msg.data += "|"
        self.hz_pub.publish(msg)


if __name__ == "__main__":
    rospy.init_node("my_hz", anonymous=True)
    monitor = RostopicHzMonitor()
    monitor.add_topic("/t265/odom/sample")
    monitor.add_topic("/d400/aligned_depth_to_color/image_raw")
    rospy.spin()
