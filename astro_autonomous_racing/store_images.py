#!/usr/bin/env python3
"""ROS2 bag file loader and processor for autonomous racing model training.

Extract and crop compressed images from a ROS2 bag, no cmd_vel synchronization.

Output:
    <output_dir>/
        images/
            000000.jpg
            000001.jpg
            ...
"""

import csv
import io
import sys
from pathlib import Path

from PIL import Image

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


# ── Topics ────────────────────────────────────────────────────────────────────
IMAGE_TOPIC = '/camera/camera/color/image_raw/compressed'
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


class ImageExtractor:
    def __init__(self, messages, output_dir, image_format='jpg'):
        self.messages     = messages
        self.output_dir   = Path(output_dir)
        self.image_format = image_format

        self.image_msgs = [(i, ts, m) for i, (ts, t, m) in enumerate(messages)
                           if t == IMAGE_TOPIC]

        print(f'Total messages : {len(self.messages):,}')
        print(f'Image messages : {len(self.image_msgs):,}')

        if not self.image_msgs:
            raise RuntimeError(f'No messages found on topic "{IMAGE_TOPIC}".')

    def process(self):
        """Extract and crop all images to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = self.output_dir / 'images'
        images_dir.mkdir(exist_ok=True)

        for idx, (img_idx, img_ts, img_msg) in enumerate(self.image_msgs):
            try:
                image = Image.open(io.BytesIO(bytes(img_msg.data)))
                width, height = image.size
                image = image.crop((0, 250, width, height))

                image_filename = f'{img_idx:06d}.{self.image_format}'
                image.save(images_dir / image_filename)
            except Exception as exc:
                print(f'  [WARN] Could not save image {img_idx}: {exc}')
                continue

            if idx % 50 == 0 or idx == len(self.image_msgs) - 1:
                print(f'  Saved {idx + 1}/{len(self.image_msgs)} frames …', end='\r')

        print(f'\nDone. Images saved to: {images_dir}')


def main():
    plain_args = [
        a for a in sys.argv[1:]
        if not a.startswith('--ros-args')
        and not a.startswith('-r')
        and not a.startswith('__')
    ]

    if len(plain_args) < 2:
        print('Usage: ros2 run <pkg> extract_images <bag_path> <output_dir>')
        return

    bag_path   = plain_args[0]
    output_dir = plain_args[1]

    print(f'Loading bag: {bag_path}')
    try:
        messages = load_bag(bag_path)
        print(f'Loaded {len(messages):,} messages from bag.')
    except Exception as exc:
        print(f'Error loading bag: {exc}')
        return

    extractor = ImageExtractor(messages, output_dir)
    extractor.process()


if __name__ == '__main__':
    main()