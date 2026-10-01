import torch
import torch.nn as nn

class LSTM24HourPredictor(nn.Module):
    def __init__(self, num_features, hidden_dim=64, num_layers=2):
        super(LSTM24HourPredictor, self).__init__()
        
        # 1. The LSTM Layer
        # batch_first=True expects dimensions: (batch, sequence_length, features)
        self.lstm = nn.LSTM(
            input_size=num_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )
        
        # 2. The Fully Connected Output Layer
        # Maps the LSTM hidden states back to your target feature space
        self.linear = nn.Linear(hidden_dim, num_features)
        
    def forward(self, x):
        # x shape expected: [batch_size, 24, num_features]
        
        # lstm_out shape: [batch_size, 24, hidden_dim]
        # (h_n, c_n) are the hidden/cell states, which we don't need for the output sequence
        lstm_out, _ = self.lstm(x)
        
        # Pass every timestep's hidden state through the linear layer
        # output shape: [batch_size, 24, num_features]
        predictions = self.linear(lstm_out)
        
        return predictions

if __name__ == "__main__":
    # Example dimensions
    BATCH_SIZE = 32
    TIMESTEPS = 24  
    NUM_FEATURES = 20
    
    # Instantiate the model
    model = LSTM24HourPredictor(num_features=NUM_FEATURES, hidden_dim=128, num_layers=2)
    
    # Create dummy tensor representing [batches, 24hr, features]
    dummy_input = torch.randn(BATCH_SIZE, TIMESTEPS, NUM_FEATURES)
    
    # Forward pass
    dummy_output = model(dummy_input)
    
    print(f"Input Shape:  {list(dummy_input.shape)}")
    print(f"Output Shape: {list(dummy_output.shape)}") 