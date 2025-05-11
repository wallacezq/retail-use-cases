#!/bin/bash

source activate-conda.sh
activate_conda
conda activate ovlangvidsumm

if [ "$1" == "--skip" ]; then
	echo "Skipping sample video download"
else
    # Download sample video
    wget https://github.com/intel-iot-devkit/sample-videos/raw/master/one-by-one-person-detection.mp4
fi

#echo "Starting http server for video hosting"
#python -m http.server 8002 &
echo "Starting FastAPI app"
uvicorn api.app:app &
APP_PID=$!
sleep 10

echo "Running Video Summarizer"
#PYTHONPATH=. python summarizer/video_summarizer.py $INPUT_FILE MiniCPM_INT8/ -d $DEVICE -r $RESOLUTION_X $RESOLUTION_Y -p "$PROMPT" -o "output-test.json"
streamlit run summarizer/streamlit_merge.py --server.port 8501 &
MERGER_PID=$!
streamlit run summarizer/streamlit_rag.py --server.port 8502
#streamlit run streamlit_test.py --server.port 8502

# terminate fastapi app after video summarization concludes
kill $APP_PID
kill $MERGER_PID
#pkill -f "python -m http.server 8002"
