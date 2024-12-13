import pandas as pd

# Read the data
file_path = "./results/link_gpt4o.csv"  # Replace with the actual file path
data = pd.read_csv(file_path)

# Define conditions for classification
# True Positive (TP): label = 1 and suspicous = 'no'
# True Negative (TN): label = 0 and suspicous = 'yes'
# False Positive (FP): label = 0 and suspicous = 'no'
# False Negative (FN): label = 1 and suspicous = 'yes'

data['TP'] = (data['label'] == 1) & (data['suspicious'] == 'no')
data['TN'] = (data['label'] == 0) & (data['suspicious'] == 'yes')
data['FP'] = (data['label'] == 0) & (data['suspicious'] == 'no')
data['FN'] = (data['label'] == 1) & (data['suspicious'] == 'yes')

# Count the occurrences
true_positives = data['TP'].sum()
true_negatives = data['TN'].sum()
false_positives = data['FP'].sum()
false_negatives = data['FN'].sum()

# Output the results
print(f"True Positives: {true_positives}")
print(f"True Negatives: {true_negatives}")
print(f"False Positives: {false_positives}")
print(f"False Negatives: {false_negatives}")