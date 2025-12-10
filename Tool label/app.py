import os
import pandas as pd
import json
from flask import Flask, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import io
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.csv'):
        try:
            # Read the CSV file
            df = pd.read_csv(file)
            
            # Validate required columns
            if 'Sentences' not in df.columns:
                return jsonify({'error': 'CSV must contain a "Sentences" column'}), 400
            
            # Ensure label columns exist and are numeric (0 or 1), handle None/NaN
            label_cols = ['E', 'S', 'G', 'I']
            for col in label_cols:
                if col not in df.columns:
                    df[col] = 0  # Initialize with 0 if column is missing
                else:
                    # Convert to numeric, coercing errors to NaN, then fill NaN with 0
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                    # Ensure values are only 0 or 1
                    df[col] = df[col].apply(lambda x: 1 if x == 1 else 0)
            
            # Generate a unique session ID for this file
            session_id = str(uuid.uuid4())
            
            # Save the processed dataframe to a temporary file
            temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.csv")
            df.to_csv(temp_file_path, index=False)
            
            # Store the session ID in the user's session
            session['csv_session_id'] = session_id
            
            # Calculate initial counts
            counts = {col: int(df[col].sum()) for col in label_cols}
            
            # Return success with data summary
            return jsonify({
                'success': True,
                'message': 'File uploaded successfully',
                'rows': len(df),
                'counts': counts
            })
            
        except Exception as e:
            return jsonify({'error': f'Error processing CSV: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file format. Please upload a CSV file'}), 400

@app.route('/get_sentence', methods=['GET'])
def get_sentence():
    index = request.args.get('index', 0, type=int)
    
    if 'csv_session_id' not in session:
        return jsonify({'error': 'No CSV file loaded'}), 400
    
    try:
        # Load the CSV file
        session_id = session['csv_session_id']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.csv")
        df = pd.read_csv(file_path)
        
        if index < 0 or index >= len(df):
            return jsonify({'error': 'Index out of range'}), 400
        
        # Get the sentence and labels
        sentence = df.loc[index, 'Sentences']
        labels = {col: int(df.loc[index, col]) for col in ['E', 'S', 'G', 'I']}
        
        return jsonify({
            'success': True,
            'sentence': sentence,
            'labels': labels,
            'total': len(df),
            'current': index + 1
        })
        
    except Exception as e:
        return jsonify({'error': f'Error retrieving sentence: {str(e)}'}), 500

@app.route('/update_sentence', methods=['POST'])
def update_sentence():
    if 'csv_session_id' not in session:
        return jsonify({'error': 'No CSV file loaded'}), 400
    
    try:
        data = request.json
        index = data.get('index', 0)
        sentence = data.get('sentence', '')
        labels = data.get('labels', {})
        
        # Load the CSV file
        session_id = session['csv_session_id']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.csv")
        df = pd.read_csv(file_path)
        
        if index < 0 or index >= len(df):
            return jsonify({'error': 'Index out of range'}), 400
        
        # Update the sentence and labels
        df.loc[index, 'Sentences'] = sentence
        for col, value in labels.items():
            if col in df.columns:
                df.loc[index, col] = 1 if value else 0
        
        # Save the updated dataframe
        df.to_csv(file_path, index=False)
        
        # Calculate updated counts
        counts = {col: int(df[col].sum()) for col in ['E', 'S', 'G', 'I']}
        
        return jsonify({
            'success': True,
            'message': 'Sentence updated successfully',
            'counts': counts
        })
        
    except Exception as e:
        return jsonify({'error': f'Error updating sentence: {str(e)}'}), 500

@app.route('/export', methods=['GET'])
def export_csv():
    if 'csv_session_id' not in session:
        return jsonify({'error': 'No CSV file loaded'}), 400
    
    try:
        # Load the CSV file
        session_id = session['csv_session_id']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.csv")
        
        # Return the file for download
        return send_file(
            file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name='labeled_data.csv'
        )
        
    except Exception as e:
        return jsonify({'error': f'Error exporting CSV: {str(e)}'}), 500

@app.route('/get_stats', methods=['GET'])
def get_stats():
    if 'csv_session_id' not in session:
        return jsonify({'error': 'No CSV file loaded'}), 400
    
    try:
        # Load the CSV file
        session_id = session['csv_session_id']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.csv")
        df = pd.read_csv(file_path)
        
        # Calculate counts
        counts = {col: int(df[col].sum()) for col in ['E', 'S', 'G', 'I']}
        
        return jsonify({
            'success': True,
            'total': len(df),
            'counts': counts
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting stats: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
