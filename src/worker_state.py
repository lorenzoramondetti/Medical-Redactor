import threading

worker_lock = threading.Lock()
worker_results = {
    'processed_data': {},
    'original_findings': {},
    'manual_rects': {},
    'file_buffers': {},
    'file_objs': {},
    'patient_uuids': {}
}
worker_status = {
    'running': False,
    'error': None
}
