# Graffiti
---
## About

Graffiti is a cloudlet based social media application which allows users to annotate their surroundings and share these annotations with other users.  It is like public virtual graffiti that covers the world, allowing users to share experiences through augmented reality.  This research was done in collaboration with Professor Satyanarayanan and Dr. Zhuo Chen from Carnegie Mellon University and was funded by the NSF.  The cloudlet interface code was built on the Gabriel Cognitive Assistant platform.

## How it Works

This project, at its core, uses SURF feature matching against a key point database to retrieve and display annotations.  SURF is a faster but less accurate version of SIFT.  When a user adds an annotation, they must take an image of the object they want to draw on.  This image is stored in the key point database, along with the relative location of the annotation.  When a user is walking around, their video stream queries the database for matches using FLANN (a faster approximate nearest neighbor algorithm).  Once a match is found, a homographic matrix is computed and the querying is stopped.  The annotation is then displayed and tracked using optical flow algorithms.

## Installation

First, clone the Gabriel Cognitive Assistant repository from [here]:https://github.com/cmusatyalab/gabriel.

Next, install the Android client on your android device.
