"""ROS2 bag file loader and processor for autonomous racing model training.

Extract compressed images from a ROS2 bag and synchronize them
with /cmd_vel.angular.z values using nearest-timestamp matching.
 
Output:
    <output_dir>/
        images/
            000000_<cmd_vel.angular.z>.jpg   
        sync_data.csv                   (index, timestamp_ns, image_file, angular_z)
"""


import argparse
import csv
import io
import os
import sys
from pathlib import Path
 
from PIL import Image
 
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
 
 
# ── Topics ────────────────────────────────────────────────────────────────────
IMAGE_TOPIC   = '/camera/camera/color/image_raw/compressed'
CMD_VEL_TOPIC = '/cmd_vel_joy'
# ──────────────────────────────────────────────────────────────────────────────

def load_bag(bag_path):
    """Read all messages from a bag and return sorted by timestamp."""
    reader = rosbag2_py.SequentialReader()
    storage_options = rosbag2_py.StorageOptions(uri=bag_path, storage_id='sqlite3')
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format='cdr',
        output_serialization_format='cdr',
    )
    reader.open(storage_options, converter_options)

    topic_types = {}
    for meta in reader.get_all_topics_and_types():
        topic_types[meta.name] = meta.type

    messages = []
    while reader.has_next():
        topic, data, timestamp = reader.read_next()
        msg_type = get_message(topic_types[topic])
        msg = deserialize_message(data, msg_type)
        messages.append((timestamp, topic, msg))

    messages.sort(key=lambda x: x[0])
    return messages


class BagProcessor:
    def __init__(self, messages,output_dir, image_format='jpg'):    
        self.messages = messages
        self.output_dir   = Path(output_dir)
        self.image_format = image_format
    
        # Separate indices per topic for easier processing
        self.image_msgs = [(i, ts, m) for i, (ts, t, m) in enumerate(messages)
                           if t == IMAGE_TOPIC]
        self.cmd_vel_msgs = [(i, ts, m) for i, (ts, t, m) in enumerate(messages)
                          if t == CMD_VEL_TOPIC]

        print(f'Total messages  : {len(self.messages):,}')
        print(f'Image messages  : {len(self.image_msgs):,}')
        print(f'cmd_vel messages: {len(self.cmd_vel_msgs):,}')
 
        if not self.image_msgs:
            raise RuntimeError(f'No messages found on topic "{IMAGE_TOPIC}".')
        if not self.cmd_vel_msgs:
            raise RuntimeError(f'No messages found on topic "{CMD_VEL_TOPIC}".')
       
    def process(self):
        """Extract images and synchronize with cmd_vel.angular.z values."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = self.output_dir / 'images'
        images_dir.mkdir(exist_ok=True)

        sync_data_path = self.output_dir / 'sync_data.csv'
        with sync_data_path.open('w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['index', 'timestamp_ns', 'image_file', 'angular_z'])

            for img_idx, img_ts, img_msg in self.image_msgs:
                # Find nearest cmd_vel message by timestamp
                nearest_cmd_vel = min(
                    self.cmd_vel_msgs,
                    key=lambda x: abs(x[1] - img_ts)
                )
                _, cmd_vel_ts, cmd_vel_msg = nearest_cmd_vel

                # Extract angular.z value
                angular_z = cmd_vel_msg.angular.z

                # Save image to disk
                img_bytes = io.BytesIO(img_msg.data)
                image = Image.open(img_bytes)
                width, height=image.size
                image = image.crop((0,250,width,height)) 
                image_filename = f'{img_idx:06d}_{angular_z:.3f}.{self.image_format}'
                image_path = images_dir / image_filename
                image.save(image_path)

                # Write synchronization data to CSV
                writer.writerow([img_idx, img_ts, image_filename, angular_z])
                

def main():
    # Strip ROS2 internal args (--ros-args, -r remaps, __node:= etc.)
    # Positional args: ros2 run <pkg> extract_and_sync <bag_path> <output_dir>
    plain_args = [
        a for a in sys.argv[1:]
        if not a.startswith('--ros-args')
        and not a.startswith('-r')
        and not a.startswith('__')
    ]
 
    if len(plain_args) >= 1:
        bag_path = plain_args[0]
    if len(plain_args) >= 2:
        output_dir = plain_args[1]
 
    print(f'Loading bag: {bag_path}')
    try:
        messages = load_bag(bag_path)
        print(f'Loaded {len(messages):,} messages from bag.')
    except Exception as exc:
        print(f'Error loading bag: {exc}')
        return
 
    print(f'Loaded {len(messages):,} messages.')
 
    processor = BagProcessor(messages, output_dir)
    processor.process()


if __name__ == '__main__':
    main()
    