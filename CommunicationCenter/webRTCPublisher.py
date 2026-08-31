#  This file is not currently used


import av
import numpy as np
from aiortc import VideoStreamTrack

class AnnotatedFrameTrack(VideoStreamTrack):
    """
    This class's job: whenever WebRTC asks 'give me the next video frame',
    grab the latest processed frame from our VideoStream and hand it over.
    """
    def __init__(self, video_stream):
        super().__init__()  # required setup from the parent class
        self.video_stream = video_stream

    async def recv(self):
        # next_timestamp() just figures out the correct timing info
        # so the video plays smoothly, not too fast/slow
        pts, time_base = await self.next_timestamp()

        frame = self.video_stream.get_latest()
        if frame is None:
            # if no frame is ready yet, send a blank black frame
            # instead of crashing
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        video_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame