import cv2
import streamlit as st
import numpy as np
import urllib.request
from sklearn.neighbors import KNeighborsClassifier
import serial
import requests
import geocoder
from urllib.parse import urlencode
import random

#Hi welcome to my code lol

arduino = serial.Serial('COM5', 9600, timeout=1)
esp32_url = 'http://192.168.1.113/cam-hi.jpg'
post_url = 'https://3124-2607-fea8-d00-5060-194d-8b78-b113-f42b.ngrok-free.app/addSighting'

if "faces" not in st.session_state:
    st.session_state["faces"] = []
    st.session_state["names"] = []
    st.session_state["relationships"] = []
    st.session_state["face_size"] = (0, 0)
if "model" not in st.session_state:
    st.session_state["model"] = None
if "captured_face" not in st.session_state:
    st.session_state["captured_face"] = None
if "stop" not in st.session_state:
    st.session_state["stop"] = False
if "notified_faces" not in st.session_state:
    st.session_state["notified_faces"] = set()

def get_location():
    try:
        g = geocoder.ip('me') 
        return g.latlng  
    except Exception as e:
        st.error(f"Error retrieving location: {e}")
        return None

def register_face():
    st.write("Look at the camera and wait for faces to be captured.")
    placeholder = st.empty()
    face_captured = False

    while not face_captured:
        img_resp = urllib.request.urlopen(esp32_url)
        img_array = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        frame = cv2.imdecode(img_array, -1)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = faceCascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            for (x, y, w, h) in faces:
                face = gray[y:y+h, x:x+w]
                st.session_state["captured_face"] = face
                st.session_state["face_size"] = (w, h)
                st.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB", use_column_width=True)
            face_captured = True

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        placeholder.image(rgb_frame, channels="RGB", use_column_width=True)

def save_face(name, relation):
    if st.session_state["captured_face"] is not None:
        face = cv2.resize(st.session_state["captured_face"], st.session_state["face_size"])
        flattened_face = face.flatten()
        st.session_state["faces"].append(flattened_face)
        st.session_state["names"].append(name)
        st.session_state["relationships"].append(relation)
        st.success(f"Face registered for {name} ({relation})")
        st.session_state["captured_face"] = None
        train_model()
    else:
        st.warning("No face captured. Please try again.")

def train_model():
    if len(st.session_state["faces"]) > 0:
        sample_face_length = len(st.session_state["faces"][0])
        for face in st.session_state["faces"]:
            if len(face) != sample_face_length:
                st.error(f"Face size mismatch: {len(face)} != {sample_face_length}")
                return

        knn = KNeighborsClassifier(n_neighbors=1)
        knn.fit(st.session_state["faces"], st.session_state["names"])
        st.session_state["model"] = knn
        st.success("Model trained with the registered faces.")

def recognize_faces():
    if st.session_state["model"] is None:
        st.warning("No model trained yet. Please register faces first.")
        return

    st.write("Press the 'Stop' button to quit the camera stream.")
    placeholder = st.empty()

    if st.button("Stop", key="stop_button"):
        st.session_state["stop"] = True

    while not st.session_state.get("stop", False):
        img_resp = urllib.request.urlopen(esp32_url)
        img_array = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        frame = cv2.imdecode(img_array, -1)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = faceCascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face, st.session_state["face_size"]).flatten()
            name = st.session_state["model"].predict([face_resized])[0]
            index = st.session_state["names"].index(name)
            relation = st.session_state["relationships"][index]
            label = f"{name} ({relation})"
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            arduino.write(f"{label}\n".encode())

            if name not in st.session_state["notified_faces"]:
                location = get_location()
                if location:
                    lat, lon = location
                    lat_mod = lat + random.randint(1, 100)
                    lon_mod = lon + random.randint(1, 100) #This is to prevent anyone from getting my actual address
                    location_str = f"{lat_mod},{lon_mod}"
                else:
                    location_str = "Unknown,Unknown"

                params = {
                    "name": name,
                    "relationship": relation,
                    "location": location_str
                }
                query_string = urlencode(params)
                request_url = f"{post_url}?{query_string}"

                st.write(f"Sending GET request to: {request_url}")  

                try:
                    response = requests.get(request_url)
                    st.write(f"Response Status Code: {response.status_code}")
                    st.write(f"Response Text: {response.text}")

                    if response.status_code == 200:
                        st.session_state["notified_faces"].add(name)
                        st.success(f"Notification sent for {name} ({relation})")
                    else:
                        st.error(f"Failed to send notification: {response.status_code}")
                except Exception as e:
                    st.error(f"Error sending GET request: {e}")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        placeholder.image(rgb_frame, channels="RGB", use_column_width=True)

st.title("Face Registration and Recognition")

if st.button("Register Face"):
    register_face()

if st.session_state["captured_face"] is not None:
    name = st.text_input("Enter your name:")
    relation = st.text_input("Enter your relation (e.g., friend, family, colleague):")
    if name and relation:
        save_face(name, relation)

if st.button("Recognize Faces"):
    st.session_state["stop"] = False
    recognize_faces()

arduino.close()
