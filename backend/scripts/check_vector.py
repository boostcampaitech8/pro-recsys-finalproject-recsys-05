import json

with open('app/data/games_metadata_with_vector.jsonl', encoding='utf-8') as f:
    line = f.readline()
    data = json.loads(line)
    
    print(f"appid: {data.get('appid')}")
    print(f"name: {data.get('name')}")
    print(f"has_vector: {'vector' in data}")
    
    if 'vector' in data and data['vector']:
        print(f"vector_length: {len(data['vector'])}")
        print(f"vector_sample: {data['vector'][:5]}")
    else:
        print("No vector field found")
