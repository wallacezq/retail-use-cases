import threading
import time
import queue
import streamlit as st
import streamlit.components.v1 as components
import argparse

from ov_lvm_wrapper import stream_queue
from streamlit_summarizer import summarizer_main, merge_queue

def update_merge_summary_in_session_state(merged_summary):
    st.session_state['merged_summary'] = merged_summary
    print("Updated merged summary session state!")

def run_summarization(args):
    summarizer_main(args)

def poll_streaming_results(text_placeholder, stop_signal):
    streamed_text = ""
    while not stop_signal.is_set() or not stream_queue.empty():
        try:
            token = stream_queue.get(timeout=0.1)
            streamed_text += token
            text_placeholder.markdown(
                f"""
                <div id="chunk_scrollable" style='height:400px; overflow-y:auto;'>
                    <pre>{streamed_text}</pre>
                </div>
                <script>
                    var container = document.getElementById('chunk_scrollable');
                    container.scrollTop = container.scrollHeight;
                </script>
                """,
                unsafe_allow_html=True
            )
        except queue.Empty:
            continue
    return streamed_text

def poll_merge_results(merge_placeholder, stop_signal):
    merged_summary = ""
    while not stop_signal.is_set() or not merge_queue.empty():
        try:
            summary = merge_queue.get(timeout=0.1)
            print(f"Recieved merged summary: {summary}")
            merged_summary += summary
            update_merge_summary_in_session_state(merged_summary)
            merge_placeholder.markdown(
                f"""
                <div id="merge_scrollable" style='height:400px; overflow-y:auto;'>
                    <pre>{merged_summary}</pre>
                </div>
                <script>
                    var container = document.getElementById('merge_scrollable');
                    container.scrollTop = container.scrollHeight;
                </script>
                """,
                unsafe_allow_html=True
            )
        except queue.Empty:
            continue
    return merged_summary

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

        merge_placeholder = st.empty()
        text_placeholder = st.empty()

        # Setup stop signal
        stop_signal = threading.Event()

        # Launch inference in background
        summarize_thread = threading.Thread(target=run_summarization, args=(args,))
        summarize_thread.start()

        # Launch background pollers
        chunk_thread = threading.Thread(target=poll_streaming_results, args=(text_placeholder, stop_signal))
        merge_thread = threading.Thread(target=poll_merge_results, args=(merge_placeholder, stop_signal))

        chunk_thread.start()
        merge_thread.start()

        # Start polling for stream results
        poll_streaming_results(text_placeholder, stop_signal)
        poll_merge_results(merge_placeholder, stop_signal)

        summarize_thread.join()
        stop_signal.set()

        chunk_thread.join()
        merge_thread.join()

        st.success("Summarization complete!")
