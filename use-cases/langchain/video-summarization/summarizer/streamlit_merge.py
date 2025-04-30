import threading
import time
import queue
import streamlit as st
import streamlit.components.v1 as components
import argparse
from queue import Queue

stream_result_queue = Queue()
merge_result_queue = Queue()

from ov_lvm_wrapper import stream_queue
from streamlit_summarizer import summarizer_main, merge_queue

def run_summarization(args):
    summarizer_main(args)

def poll_streaming_results(stop_signal):
    streamed_text = ""
    while not stop_signal.is_set() or not stream_queue.empty():
        try:
            token = stream_queue.get(timeout=0.1)
            streamed_text += token
            stream_result_queue.put(streamed_text)
        except queue.Empty:
            continue

def poll_merge_results(stop_signal):
    merge_summary = ""
    while not stop_signal.is_set() or not merge_queue.empty():
        try:
            summary = merge_queue.get(timeout=0.1)
            print(f"\n\nRecieved merged summary in poll results: {summary}\n\n")
            merge_summary += summary
            merge_result_queue.put(merge_summary)
        except queue.Empty:
            continue

st.title("🎥 Streaming Video Summarizer")

uploaded_file = st.file_uploader("Upload a video", type=["mp4", "avi", "mov"])

if uploaded_file is not None:
    st.video(uploaded_file)

    if st.button("Start Summarization"):
        with open("uploaded_video.mp4", "wb") as f:
            f.write(uploaded_file.read())

        args = argparse.Namespace(
            video_file='uploaded_video.mp4',
            model_dir='MiniCPM_INT8/',
            prompt="""
            As an expert investigator, please analyze this video. Summarize the video, generating an
            Overall Summary, Activity Observed, and Potential Suspicious Activity. 
            It should be formmatted as such:

            **Overall Summary**
            Here is a detailed description of the video.

            **Activity Observed**
            1) Here is a bullet point list of the activities observed. If nothing is observed>

            **Potential Suspicious Activity**
            1) Here is a bullet point list of suspicious behavior (if any) to highlight.
            """,
            device='GPU.1',
            max_new_tokens=256,
            max_num_frames=32,
            chunk_duration=15,
            chunk_overlap=2,
            merge_cadence=30,
            resolution=[480, 270],
            outfile='',
            extend_to_vertex=True,
            anomaly_thresh=0.5,
            cloud_model="gemini-2.0-flash-exp"
        )

        chunk_placeholder = st.empty()
        merge_placeholder = st.empty()

        # Setup stop signal
        stop_signal = threading.Event()

        # Launch inference in background
        summarize_thread = threading.Thread(target=run_summarization, args=(args,))
        chunk_thread = threading.Thread(target=poll_streaming_results, args=(stop_signal,))
        merge_thread = threading.Thread(target=poll_merge_results, args=(stop_signal,))

        summarize_thread.start()
        chunk_thread.start()
        merge_thread.start()

        streamed_text = ""
        merge_summary = ""

        while summarize_thread.is_alive() or not stop_signal.is_set():
            while not stream_result_queue.empty():
                streamed_text = stream_result_queue.get()
                chunk_placeholder.markdown(
                    f"""
                    <div id="scrollable" style='height:400px; overflow-y:auto;'>
                        <pre>{streamed_text}</pre>
                    </div>
                    <script>
                        var container = document.getElementById('scrollable');
                        container.scrollTop = container.scrollHeight;
                    </script>
                    """,
                    unsafe_allow_html=True
                )
            while not merge_result_queue.empty():
                merge_summary = merge_result_queue.get()
                merge_placeholder.markdown(
                    f"""
                    <div id="scrollable" style='height:400px; overflow-y:auto;'>
                        <pre>{merge_summary}</pre>
                    </div>
                    <script>
                        var container = document.getElementById('merge_scrollable');
                        container.scrollTop = container.scrollHeight;
                    </script>
                    """,
                    unsafe_allow_html=True
                )
            time.sleep(0.1)

        stop_signal.set()
        chunk_thread.join()
        merge_thread.join()
        summarize_thread.join()

        st.success("Summarization complete!")
