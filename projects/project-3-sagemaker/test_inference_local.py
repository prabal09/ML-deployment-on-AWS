from inference import model_fn, input_fn, predict_fn, output_fn

# Simulate container startup
model = model_fn(".")  # loads model.pkl from current directory

# Simulate a single-sample request
input_data = input_fn('{"features":[5.1,3.5,1.4,0.2]}', "application/json")
prediction = predict_fn(input_data, model)
body, content_type = output_fn(prediction, "application/json")
print("Single sample:", body)
# Expected: {"prediction": 0, "class_name": "setosa"}

# Simulate a batch request
batch_body = '{"instances":[[5.1,3.5,1.4,0.2],[6.2,3.4,5.4,2.3],[5.9,3.0,5.1,1.8]]}'
input_data = input_fn(batch_body, "application/json")
prediction = predict_fn(input_data, model)
body, content_type = output_fn(prediction, "application/json")
print("Batch:", body)
# Expected: [{"prediction":0,"class_name":"setosa"}, ...]
