import threading
import time
import queue
import streamlit as st
import streamlit.components.v1 as components
import argparse
from queue import Queue
import re
import os

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

st.set_page_config(layout="wide")

st.title("🎥 Streaming Video Summarizer")

# Initialize session state
if 'streamed_text' not in st.session_state:
    st.session_state['streamed_text'] = ''

if 'merged_summary' not in st.session_state:
    st.session_state['merged_summary'] = ''

# Split the page into two columns
spacer_col, left_col, right_col = st.columns([0.05, 0.55, 0.4])  # Adjust ratio as needed

video_path = 'one-by-one-person-detection.mp4'

with left_col:
    #uploaded_file = st.file_uploader("Upload a video", type=["mp4", "avi", "mov"])
    #if uploaded_file is not None:
    #    st.video(uploaded_file)
    #    start_button_pressed = st.button("Start Summarization")
    if os.path.exists(video_path):
        st.video(video_path)
    else:
        st.warning("The video file cannot be found")
    start_button_pressed = st.button("Start Summarization")

with right_col:
    st.markdown("### 📄 Chunk Summaries")
    chunk_placeholder = st.empty()
    chunk_placeholder.markdown(
        f"""
        <div id="scrollable" style='height:500px; overflow-y:auto;'>
            <pre>{st.session_state['streamed_text']}</pre>
        </div>
        <script>
            var container = document.getElementById('scrollable');
            if (container) {{
                container.scrollTop = container.scrollHeight;
            }}
        </script>
        """,
        unsafe_allow_html=True
    )

with left_col:
    st.markdown("### 🧠 Merged Summaries")
    merge_placeholder = st.empty()
    merge_placeholder.markdown(
        f"""
        <div id="merge_scrollable" style='height:400px; overflow-y:auto;'>
            <pre>{st.session_state['merged_summary']}</pre>
        </div>
        <script>
            var container = document.getElementById('merge_scrollable');
            if (container) {{
                container.scrollTop = container.scrollHeight;
            }}
        </script>
        """,
        unsafe_allow_html=True
    )

if start_button_pressed:
    args = argparse.Namespace(
        video_file='one-by-one-person-detection.mp4',
        model_dir='MiniCPM_INT8/',
        prompt="""
        As an expert investigator, please analyze this video. Summarize the video, generating an
        Overall Summary, Activity Observed, and Potential Suspicious Activity. 
        It should be formatted as such:

        Overall Summary
        Here is a detailed description of the video.

        Activity Observed
        1) Here is a bullet point list of the activities observed.

        Potential Suspicious Activity
        1) Here is a bullet point list of suspicious behavior (if any) to highlight.
        """,
        device='GPU.1',
        max_new_tokens=256,
        max_num_frames=64,
        chunk_duration=15,
        chunk_overlap=2,
        merge_cadence=30,
        resolution=[480, 270],
        outfile='',
        extend_to_vertex=True,
        anomaly_thresh=0.5,
        cloud_model="gemini-2.0-flash-exp"
    )

    stop_signal = threading.Event()
    summarize_thread = threading.Thread(target=run_summarization, args=(args,))
    summarize_thread.start()

    # Define these before the loop
    chunk_duration = args.chunk_duration
    chunk_overlap = args.chunk_overlap
    chunk_index = 0
    current_time = 0
    chunk_summaries = []

    while summarize_thread.is_alive() or not stream_queue.empty() or not merge_queue.empty():
        try:
            if not stream_queue.empty():
                token = stream_queue.get(timeout=0.1)
                st.session_state['streamed_text'] += token
                safe_text = (st.session_state['streamed_text'].replace('\n', '<br>').replace('[CHUNK ', '<br><strong>[CHUNK ').replace('sec]', 'sec]</strong>'))
                chunk_placeholder.markdown(
                    f"""
                    <div id="scrollable" style='height:500px; overflow-y:auto;'>
                       <div style="white-space: pre-wrap;">{safe_text}</div>
                    </div>
                    <script>
                        var container = document.getElementById('scrollable');
                        container.scrollTop = container.scrollHeight;
                    </script>
                    """,
                    unsafe_allow_html=True
                )
        except queue.Empty:
            pass

        try:
            if not merge_queue.empty():
                summary = merge_queue.get(timeout=0.1)
                st.session_state['merged_summary'] += summary
                safe_merged_text = (st.session_state['merged_summary'].replace('\n', '<br>').replace('[MERGED SUMMARY ', '<br><strong>[MERGED SUMMARY ').replace('sec]', 'sec]</strong>'))
                merge_placeholder.markdown(
                    f"""
                    <div id="merge_scrollable" style='height:400px; overflow-y:auto;'>
                        <div style="white-space: pre-wrap;">{safe_merged_text}</div>
                    </div>
                    <script>
                        var container = document.getElementById('merge_scrollable');
                        container.scrollTop = container.scrollHeight;
                    </script>
                    """,
                    unsafe_allow_html=True
                )
        except queue.Empty:
            pass

    summarize_thread.join()
    stop_signal.set()
    st.success("Summarization complete!")

