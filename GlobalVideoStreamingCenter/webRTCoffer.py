# This file is not in Use

import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription
import firebase_admin
from firebase_admin import credentials, firestore

from CommunicationCenter.webRTCPublisher import AnnotatedFrameTrack
from CommunicationCenter.Streaming import VideoStream

cred = credentials.Certificate("CloudCenter/firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

SESSION_DOC = db.collection("calls").document("live_stream")


async def wait_for_ice_gathering(pc):
    # Keep checking until the laptop has finished gathering
    # all its possible "addresses" (ICE candidates)
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.1)


async def start_video_offer():
    video_stream = VideoStream()
    video_stream.start()

    from aiortc import RTCConfiguration, RTCIceServer

    config = RTCConfiguration(iceServers=[
        RTCIceServer(urls="stun:stun.l.google.com:19302"),
        RTCIceServer(
            urls="turn:free.expressturn.com:3478",
            username="000000002103375375",
            credential="QHdW99nsbMmucuKVLeiCHfhCzBM=",
        ),
        RTCIceServer(
            urls="turn:free.expressturn.com:3478?transport=tcp",
            username="000000002103375375",
            credential="QHdW99nsbMmucuKVLeiCHfhCzBM=",
        ),
    ])

    pc = RTCPeerConnection(configuration=config)
    pc.addTrack(AnnotatedFrameTrack(video_stream))

    @pc.on("iceconnectionstatechange")
    def on_ice_state_change():
        print(f"[ICE connection state]: {pc.iceConnectionState}")

    @pc.on("connectionstatechange")
    def on_connection_state_change():
        print(f"[Overall connection state]: {pc.connectionState}")

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    # NEW: wait until gathering is fully done before saving
    await wait_for_ice_gathering(pc)

    SESSION_DOC.set({
        "offer_sdp": pc.localDescription.sdp,
        "offer_type": pc.localDescription.type,
    })
    print("Offer sent (with full ICE info)! Waiting for phone's answer...")

    # NEW: keep checking Firestore for the phone's answer
    attempt = 0
    while True:
        attempt += 1
        doc = SESSION_DOC.get()
        data = doc.to_dict()
        print(f"[Check #{attempt}] Firestore doc keys: {list(data.keys()) if data else 'EMPTY'}")
        if data and data.get("answer_sdp"):
            print("Answer received from phone! Connecting...")
            answer = RTCSessionDescription(
                sdp=data["answer_sdp"], type=data["answer_type"]
            )
            await pc.setRemoteDescription(answer)
            print("Connected! Video should now be streaming.")
            break
        await asyncio.sleep(1)

    # keep running so the connection + video stays alive
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(start_video_offer())