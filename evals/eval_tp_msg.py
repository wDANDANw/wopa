import pandas as pd

# Read the data
file_path = "./results/message_local.csv"  # Replace with the actual file path
data = pd.read_csv(file_path)

# Define conditions for classification
# True Positive (TP): label = 'spam' and outcome = 'success'
# True Negative (TN): label = 'ham' and outcome = 'fail'
# False Positive (FP): label = 'ham' and outcome = 'success'
# False Negative (FN): label = 'spam' and outcome = 'fail'

data['TP'] = (data['label'] == 'ham') & (data['suspicious'] == 'no')
data['TN'] = (data['label'] == 'spam') & (data['suspicious'] == 'yes')
data['FP'] = (data['label'] == 'spam') & (data['suspicious'] == 'no')
data['FN'] = (data['label'] == 'ham') & (data['suspicious'] == 'yes')

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
