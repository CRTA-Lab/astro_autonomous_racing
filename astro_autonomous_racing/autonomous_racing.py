"""
ROS2 node from autonomus racing based on the visual data.

This node subscribes to the /camera/image_raw topic to receive images from the camera.
Then it perfroms inference using classification neural network to estimate the steering angle that is published on the /cmd_vel topic. 
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage,Joy
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import torch
import cv2
import torchvision.transforms as transforms
import torch.nn as nn
import numpy as np


#######################################################################################################################################
####     SETTING UP THE TRANSFORMATIONS AND MODEL                                                                                  ####
#######################################################################################################################################
#Transformations for the input image
transform = transforms.Compose([transforms.ToTensor(),
                                transforms.Resize((40, 60)),
                                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
                                ])


class Net(nn.Module):
    def __init__(self):
        super().__init__()

        self.conv1 = nn.Conv2d(3, 6, 5)
        self.bn1   = nn.BatchNorm2d(6)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.bn2   = nn.BatchNorm2d(16)
        self.pool = nn.MaxPool2d(2, 2)
        self.relu = nn.ReLU()

        self.fc_shared = nn.Linear(1344, 256)

        self.fc_drive1 = nn.Linear(256, 128)  
        self.fc_drive2 = nn.Linear(128,5) 
        # self.fc_stop1  = nn.Linear(256, 64)  
        # self.fc_stop2  = nn.Linear(64, 1) 

    def forward(self, x):

        x = self.pool(self.relu(self.bn1(self.conv1(x))))
        x = self.pool(self.relu(self.bn2(self.conv2(x))))
        x = torch.flatten(x, 1)

        x = self.relu(self.fc_shared(x))

        drive_logits = self.fc_drive1(x)
        drive_logits = self.relu(drive_logits)
        drive_logits = self.fc_drive2(drive_logits)
        
        # stop_logit   = self.fc_stop1(x)
        # stop_logit = self.relu(stop_logit)
        # stop_logit   = self.fc_stop2(stop_logit)
        return drive_logits


#######################################################################################################################################
####     AUTONOMOUS RACING NODE                                                                                                    ####
#######################################################################################################################################

class AutonomousRacingNode(Node):
    def __init__(self):
        super().__init__('autonomous_racing_node')
        self.driving_enabled = False
        self.subscription = self.create_subscription(
            CompressedImage,
            '/camera/camera/color/image_raw/compressed',
            self.image_callback,
            10
        )
        self.joy_sub = self.create_subscription(
            Joy,
            '/joy', 
            self.joy_callback,
            10
        )
        
        self.publisher = self.create_publisher(Twist, 
            '/cmd_vel_joy', 
            10
        )
        self.bridge = CvBridge()
        # Load your trained model 
        self.model = Net()
        self.model.load_state_dict(torch.load('steer_net_2.pth', weights_only=True))
        self.model.eval()

    def joy_callback(self, msg):
        # Button 0 = X on PS4 / A on Xbox — change index to whatever button you want
        ENABLE_BUTTON = 0
        if msg.axes[7] == 1.0:
            print("START")
            self.driving_enabled = True
            state = 'ENABLED'
        if msg.axes[7] == -1.0:
            print("STOP")
            self.driving_enabled = False
            state = 'DISABLED'

        # if msg.axes[6] == 1.0:
        #     print("Lijevo")
            
        # if msg.axes[6] == -1.0:
        #     print("Desno")
            
        

    def image_callback(self, msg):
        #Setup a default Twist message with zero velocities (stop) in case driving is not enabled
        twist_msg = Twist()
        twist_msg.linear.x = 0.0
        twist_msg.angular.z = 0.0


        # Only run inference and drive if enabled
        if not self.driving_enabled:
            self.publisher.publish(twist_msg)  # publishes zero twist = stop
            return
        
        # Convert compressed ROS Image message to OpenCV format
        np_arr = np.frombuffer(msg.data, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # Preprocess the image for your model (resize, normalize, etc.)
        input_tensor = self.preprocess_image(cv_image)
        
        # Perform inference to get the steering angle
        with torch.no_grad():
            drive_logits = self.model(input_tensor)
            soft = torch.softmax(drive_logits,dim=1)
            preds = torch.argmax(soft, dim=1)

            angle = 0
           
            #Convert the predicted class to a steering angle (this mapping depends on how you trained your model)
            if preds.item() == 0:
                angle = 0.6 
                
            elif preds.item() == 1:
                angle = 0.4 
                 
            elif preds.item() == 2:
                angle = 0
                
            elif preds.item() == 3:
                angle = -0.4 
                 
            elif preds.item() == 4:
                angle = -0.6 

        #Set the linear velocity and angular velocity based on the predicted steering angle  
        twist_msg.linear.x = 0.3
        twist_msg.angular.z = float(angle)

        # Publish the steering command
        self.publisher.publish(twist_msg)

    def preprocess_image(self, cv_image):
        """Preprocess the input image for the model."""
        # Crop the image to focus on the road 
        cv_image = cv_image[250:, :, :]
        #Apply the same transformations as during training
        input_tensor = transform(cv_image).unsqueeze(dim=0)

        return input_tensor
        

def main(args=None):
    #ROS initialization
    print("Start")
    rclpy.init(args=args)
    #Creation of a node
    aut_racing = AutonomousRacingNode()
    rclpy.spin(aut_racing)
    #Destory the node
    aut_racing.destroy_node()
    #ROS shutdown
    rclpy.shutdown()

  
if __name__ == '__main__':
  main()
