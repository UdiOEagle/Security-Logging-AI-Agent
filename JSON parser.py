import json
import csv

# Load the JSON file
with open('autosar_security_events.json', 'r') as f:
    data = json.load(f)

# Extract pdf_analyses list
pdf_analyses = data['pdf_analyses']

no_new_events_rows = []
new_events_rows = []

for analysis in pdf_analyses:
    processed_time = analysis['processed_at']
    pdf_file = analysis['pdf_file']
    events = analysis['events']
    
    # Check if first event indicates no events
    first_event = events[0]
    if 'status' in first_event and first_event['status'] == 'no_events':
        # No new events: append to No New Events.csv
        explanation = first_event['explanation']
        no_new_events_rows.append({
            'processing_time': processed_time,
            'pdf_file': pdf_file,
            'explanation': explanation
        })
    else:
        # New events: append each to New Events.csv
        for event in events:
            # Safely extract fields, skip if missing
            system_event = event.get('System event', 'N/A')
            suggested_log = event.get('Suggested log', 'N/A')
            rationale = event.get('Rationale', 'N/A')
            new_events_rows.append({
                'processed_time': processed_time,
                'pdf_file': pdf_file,
                'System event': system_event,
                'suggested log': suggested_log,
                'rationale': rationale
            })

# Write No New Events.csv
with open('No New Events.csv', 'w', newline='', encoding='utf-8') as f:
    if no_new_events_rows:
        fieldnames = ['processing_time', 'pdf_file', 'explanation']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(no_new_events_rows)
    else:
        f.write('No data\n')

# Write New Events.csv
with open('New Events.csv', 'w', newline='', encoding='utf-8') as f:
    if new_events_rows:
        fieldnames = ['processed_time', 'pdf_file', 'System event', 'suggested log', 'rationale']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_events_rows)
    else:
        f.write('No data\n')

print(f"Generated CSVs: {len(no_new_events_rows)} no-event entries, {len(new_events_rows)} new-event rows.")
