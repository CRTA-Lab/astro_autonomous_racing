# astro_autonomous_racing

ROS2 Python package for autonomous ASTRO robot racing.
Includes one node and two main scripts callable from ROS2:
- **data_preparation** - the script that prepares the bagged data for model train
- **splitter.py** - the script that splits the prepared dataset into the train/test
- **steerDS_crta.py** - the helper script that prepares the training dataest - remaps the steering angle velocity (cmd_vel.angular.z) into the 5 classifications (sharp_left, left. straight, right, sharp_right) 
- **train_net_crta.py** - the script that trains the classifcation neural network model
- **autonomous_racing** - autonomous racing deploy of trained classification model

This exercise is created by Luka Šiktar, Janko Jurdana with help of Branimir Ćaran.

---

This ROS2 package demonstrates ASTRO CNN-based autonomous racing. The main goal of the exercise is to record the model training data by driving the robot along the track and saving the visual and odometry data using **ros2 bag**. The recorded **bag** is then preprocessed to ensure the training dataset for Pytorch-based classification network that steers the robots. The classificaiton network learns by the example: The operator drives the robot and stores the images and speeds (linear and angular). Based on images and speeds remapped into 5 classes (sharp left, left, straight, right, sharp right), the model trains to classify each image to enable autonomous steering. The trained model is then deployed on ASTRO robot.


## 0. Download the package into the existing **astro_ws**

**Clone the repository**

Make sure you are inside **astro_ws/src** folder:

```bash
cd ~/astro_ws/src
git clone -b humble https://github.com/CRTA-Lab/astro_autonomous_racing.git
```

**Installing dependencies**

Make sure you are now in your main workspace folder, in this example **~/astro_ws/** \
Make sure you have [rosdep](https://docs.ros.org/en/humble/Tutorials/Intermediate/Rosdep.html) set-up.

```bash
cd ~/astro_ws/
rosdep install --from-paths src -y --ignore-src
```

**Building astro_autonomous_racing package**

Make sure you are still in your main workspace folder, in this example **~/astro_ws/**
```bash
cd ~/astro_ws/
colcon build --packages-select astro_autonomous_racing
```


## 1. Collect the dataset

The first part of the task is to record the **bag** that will then be processed as the input to the model.
The topics that we need to bag in order to train the model:
- **/camera/camera/color/image_raw/compressed**  - compressed raw image from the ASTRO
- **/cmd_vel_joy** - linear and angular velocities applied to the ASTRO via PS4 joystick

### 1.1 SSH into the Robot

Each Astro robot has a unique number. Replace `x` with your robot's number:

```bash
ssh astro@192.168.0.1x
```

Example for robot 3:
```bash
ssh astro@192.168.0.13
```


### 1.2. Check if the Docker Container is Running

```bash
docker ps
```

Look for a container named **`astro_hw`** in the output. If it is not listed, start it before continuing.



### 1.3. Enter the Docker Container

```bash
docker exec -it astro_hw /bin/bash
```

You are now inside the container with access to all ROS2 tools and the camera drivers.



### 1.4. Navigate to the Workspace Source Directory

```bash
cd /home/astro/astro_ws/src
```



### 1.5. Check for (or Create) the Bags Folder

```bash
ls
```

If a `bags` folder is not listed, create it:

```bash
mkdir bags
cd bags
```

If it already exists, just navigate into it:

```bash
cd bags
```



### 1.6. Record a ROS2 Bag

Record compressed RGB, aligned depth, and odometry from the RealSense D435:

```bash
ros2 bag record \
  /camera/camera/color/image_raw/compressed \
  /camera/camera/aligned_depth_to_color/image_raw/compressedDepth \
  /odom \
  /cmd_vel_joy
```

A timestamped folder (e.g. `rosbag2_2026_03_24-14_08_28`) will be created in the current directory.
Press **Ctrl+C** to stop recording.



### 1.7. Drive the Robot to Collect Data

While recording is running, drive the robot around the environment using the joystick or teleoperation node to capture a variety of viewpoints and depth information.



### 1.8. Download the Bag to Your Machine

The `/home/astro/astro_ws/src/bags` directory inside the Docker container is shared with the Jetson host filesystem at the same path.
You can download the recorded bag from the **Jetson** (not from inside Docker) using `scp`:

```bash
scp -r astro@192.168.0.1x:/home/astro/astro_ws/src/bags/<bag_folder_name> ~/Desktop/
```

Example:
```bash
scp -r astro@192.168.0.13:/home/astro/astro_ws/src/bags/rosbag2_2026_03_24-14_08_28 ~/Desktop/
```


## 2. Prepare the dataset

In order to prepare the dataset, the recoreded **bag** needs to be transformed firstly into visible data/ images stored in the  ``` your_ws/images ``` .

The visible data - images with the specific names:  ```**{image_id}_{cmd_vel.anglular.z}.jpg**```

The images are cropped to the bottom 1/3 because that is the most important part of an image for the model train.

Using **data_preparation**:

```bash
cd ~/astro_ws/
ros2 run astro_autonomous_racing data_preparation <bag_folder_path> ./images
```

## 3. Train the model


To train the model, firsty clone the **ASTRO_autonomous_racing_model_training_scripts** repo:

```bash
cd ~/astro_ws/
git clone https://github.com/lukasiktar/ASTRO_autonomous_racing_model_training_scripts.git
```


As the reference for classification model train use Pytorch's [Training a Classifier](https://docs.pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html)

The goal of this part is to get familiar with, train and fine tune the classifier for your needs.

Model trainer have 1 main script ```train_net_crta.py``` with 2 helper scripts ```splitter.py``` and ```steerDS_crta.py```.

### 3.1. Split the created dataset into train/test

```splitter.py``` splits the images dataset into ```images/train``` and ```images/val```.

Usage:

```bash
cd ~/astro_ws/
python3 ASTRO_autonomous_racing_model_training_scripts/splitter.py
```

### 3.2 (Optional) Modify the ```steerDS_crta.py``` if needed.

```steerDS_crta.py``` script describes the remappingg between the steering ```{cmd_vel.angular.z}```  to ``` self.class_labels = ['sharp left', 'left', 'straight', 'right', 'sharp right', 'stop']```


### 3.3 Train the model

Model training script - ```train_net_crta.py``` have multiple segments:
- **```SETTING UP THE DATASET```** - This part of the script sets up the transformations on raw images from /train /val folders to be prepared as inputs to the model. It sets up the train and validation datasets and displays the dataset's class balance and the start. **Do not change this segment**
- **```CONFIGURE CLASSIFICATION MODEL ARCHITECTURE```** - This part confiures the model architecture. Here **you** should specify the architecture. For the reference use this [PyTorch Classifer Tutorial]((https://docs.pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html))
- **```TRAINING HYPERPARAMETERS```** - Here **you** specify the model training hyperparameters: Loss function as criterion, optimizer, number of epochs.
- **```TRAINING```** - Model train segment. Here **you** specify the name of saved trained model. ```<model_name>.pth```
- **```VALIDATION```** - Validation segment, displays the confusion matrix. **Do not chnage this segment**


Start model training procedure:
```bash
cd ~/astro_ws/
python3 ASTRO_autonomous_racing_model_training_scripts/train_net_crta.py
```


The trained model will be stored into ```ASTRO_autonomous_racing_model_training_scripts/<model_name>.pth```


## 4. Deploy autonomous racing model to ASTRO

Deploy the trained model ```<model_name>.pth``` to the ASTRO for autonomous racing using ```autonomous_racing_node``` specified in  ```autonomous_racing.py```.

The deployment script - ```autonomous_racing.py``` have multiple segments:
- **```SETTING UP THE TRANSFORMATIONS AND MODEL```** - This segment is copy-paste from ```train_net_crta.py``` and it specifies the input transformations (also neccessary for the transformation of raw images that are fed to model), and model architecture (neccessary to specify the model architecture in order to create model and load the trained data from ```<model_name>.pth```)
- **```AUTONOMOUS RACING NODE```** - ROS2 node for autonomous racing. Here **you** should apply the logic that will interpret the classification model output to the steering angles. This is one of the solutions:

```bash
# Perform inference to get the steering angle
        with torch.no_grad():
            drive_logits = self.model(input_tensor)
            soft = torch.softmax(drive_logits,dim=1)
            preds = torch.argmax(soft, dim=1)

            angle = 0
           
            #Convert the predicted class to a steering angle (this mapping depends on how you trained your model)
            if preds.item() == 0:
                angle = 0.8 
                
            elif preds.item() == 1:
                angle = 0.5 
                 
            elif preds.item() == 2:
                angle = 0
                
            elif preds.item() == 3:
                angle = -0.5 
                 
            elif preds.item() == 4:
                angle = -0.8 

        #Set the linear velocity and angular velocity based on the predicted steering angle  
        twist_msg.linear.x = 0.25
        twist_msg.angular.z = float(angle)

        # Publish the steering command
        self.publisher.publish(twist_msg)
```

**Your goal is to be faster than others**