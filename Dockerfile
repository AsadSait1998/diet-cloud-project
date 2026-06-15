FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DIET_DATASET_PATH=All_Diets.csv
ENV OUTPUT_DIR=outputs

CMD ["python", "data_analysis.py"]
