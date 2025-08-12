import numpy as np
import json

# Post-processor class. Note: It must be named 'PostProcessor' for PySDK to detect and invoke it.
class PostProcessor:
    def __init__(self, json_config):
        """
        Initialize the post-processor with configuration settings.

        Parameters:
            json_config (str): JSON string containing post-processing configuration.
        """
        # Parse the JSON configuration
        self._json_config = json.loads(json_config)

        # Extract configuration parameters
        self._num_classes = int(self._json_config["POST_PROCESS"][0]["OutputNumClasses"])
        self._label_json_path = self._json_config["POST_PROCESS"][0]["LabelsPath"]
        self._input_height = int(self._json_config["PRE_PROCESS"][0]["InputH"])
        self._input_width = int(self._json_config["PRE_PROCESS"][0]["InputW"])

        # Load label dictionary from JSON file
        with open(self._label_json_path, "r") as json_file:
            self._label_dictionary = json.load(json_file)

        # Extract confidence threshold; defaults to 0.0 if not specified
        self._output_conf_threshold = float(
            self._json_config["POST_PROCESS"][0].get("OutputConfThreshold", 0.0)
        )

    def forward(self, tensor_list, details_list):
        """
        Process the raw output tensor to produce formatted detection results.

        Parameters:
            tensor_list (list): List of output tensors from the model.
            details_list (list): Additional details (e.g., quantization info); not used in this example.

        Returns:
            list: A list of dictionaries, each representing a detection result.
        """
        # Initialize a list to store detection results
        new_inference_results = []

        # The first tensor is assumed to contain all detection data.
        # Reshape it to a 1D array for easier processing.
        output_array = tensor_list[0].reshape(-1)

        index = 0  # Track current position in output_array

        # Iterate over each class
        for class_id in range(self._num_classes):
            # Read the number of detections for the current class
            num_detections = int(output_array[index])
            index += 1

            if num_detections == 0:
                # No detections for this class; move to the next one.
                continue

            # Process each detection for the current class
            for _ in range(num_detections):
                # Ensure there are enough elements for a complete detection record (4 bbox coordinates + score)
                if index + 5 > len(output_array):
                    break

                # Extract bounding box coordinates and the confidence score.
                # The format is assumed to be: [y_min, x_min, y_max, x_max, score]
                y_min, x_min, y_max, x_max = map(float, output_array[index : index + 4])
                score = float(output_array[index + 4])
                index += 5

                # Apply confidence threshold; skip detection if below threshold
                if score < self._output_conf_threshold:
                    continue

                # Convert normalized coordinates to absolute pixel values based on input dimensions
                x_min_abs = x_min * self._input_width
                y_min_abs = y_min * self._input_height
                x_max_abs = x_max * self._input_width
                y_max_abs = y_max * self._input_height

                # Build the detection result dictionary
                result = {
                    "bbox": [x_min_abs, y_min_abs, x_max_abs, y_max_abs],
                    "score": score,
                    "category_id": class_id,
                    "label": self._label_dictionary.get(str(class_id), f"class_{class_id}"),
                }
                new_inference_results.append(result)

            # If the remainder of the output_array is nearly or fully consumed, exit early.
            if index >= len(output_array) or all(v == 0 for v in output_array[index:]):
                break

        # Return the list of formatted detection results.
        return new_inference_results