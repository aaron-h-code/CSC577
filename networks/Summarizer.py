import torch
import torch.nn as nn
from torch.autograd import Variable

import pdb

# output normalized importance scores
class sLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers = 2, bidirectional = True):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        # hidde_size should be 1024
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, bidirectional = bidirectional)
        self.to_score = nn.Sequential(nn.Linear(hidden_size * 2, 1), nn.Sigmoid()) # bidirection -> scalar

    """
    Args:
        x: ResNet features, (seq_len, 1, input_size) = (seq_len, 1, 2048)
    Return:
        scores: normalized, (seq_len, 1)
    """
    def forward(self, x):
        self.lstm.flatten_parameters()
        # output: (seq_len, 1, hidden_size * 2) = (seq_len, 1, 2048)
        output, (h_n, c_n) = self.lstm(x)
        # output.squeeze(1): (seq_len, 2048)
        # scores: (seq_len, 1)
        scores = self.to_score(output.squeeze(1))

        return scores


# encoder, output a fixed length feature
class eLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers = 2, bidirectional = False):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        # hidden_size should be 1024
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, bidirectional = bidirectional)
    
    """
    Args:
        x: weighted_features, (seq_len, 1, input_size) = (seq_len, 1, 2048)
    Return:
        fixed length feature: a tuple of hidden state, each of (num_layers * 1, 1, hidden_size) = (2, 1, 1024)
    """
    def forward(self, x):
        self.lstm.flatten_parameters()
        # h_c, c_n: (num_layers * 1, 1, hidden_size) = (2, 1, 1024)
        _, (h_n, c_n) = self.lstm(x)

        return (h_n, c_n)
       

# decoder, 
class dLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers = 2, bidirectional = False):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        # hidden_size should be 2048
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, bidirectional = bidirectional)
    
    """
    Args:
        x: fixed length feature, (seq_len, 1, input_size) = (seq_len, 1, 4096)
    Return:
        decoded: decoded feature of a video, (seq_len, 1, hidden_size) = (seq_len, 1, 2048) 
    """
    def forward(self, x):
        self.lstm.flatten_parameters()
        # decoded: (seq_len, 1, hidden_size * 1) = (seq_len, 1, 2048)
        decoded, _ = self.lstm(x)

        return decoded

# consist of eLSTM and dLSTM
class VAE(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers = 2, bidirectional = False):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional

        self.elstm = eLSTM(input_size, hidden_size, num_layers, False)

        # the last hidden state of eLSTM is (num_layers * 1, 1, hidden_size)
        # = (2, 1, 1024), change it to the shape (1, 1, 1024 * 2), and then 
        # repeat it seq_len times, as the input of dLSTM
        self.dlstm = dLSTM(input_size, 2 * hidden_size, num_layers, False)

    """
    Args:
        x: weighted_features, (seq_len, 1, input_size) = (seq_len, 1, 2048)
    Return:
        decoded: decoded feature of a video, (seq_len, 1, 2 * hidden_size) = (seq_len, 1, 2048)
    """
    def forward(self, x):
        seq_len = x.size(0)
        # h_n, c_n: (num_layers * 1, 1, hidden_size) = (2, 1, 1024)
        h_n, c_n = self.elstm(x)

        # reshape h_n to (1, 1, 1024 * 2)
        h_n_reshape = h_n.view(1, 1, -1)
        # repeat seq_len times to (seq_len, 1, 2048)
        h_n_reshape = h_n_reshape.expand(seq_len, 1, h_n_reshape.data.shape[2])


        # h: (num_layers * 1, hidden_size) = (2, 2048)
        h = h_n.squeeze(1)
        
        # decoded feature: (seq_len, 1, 2 * hidden_size) = (seq_len, 1, 2048)
        decoded = self.dlstm(h_n_reshape)

        return decoded

# consist of sLSTM, VAE(eLSTM, dLSTM)
class Summarizer(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers = 2):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.slstm = sLSTM(input_size, hidden_size, num_layers, True)
        self.vae = VAE(input_size, hidden_size, num_layers)

    def forward(self, x, random_score_flag = False):
        # input sequence fream features are weighted with scores
        if not random_score_flag:
            scores = self.slstm(x)
            # weighted features: (seq_len, 1, 2048)
            weighted_features = x * scores.view(-1, 1, 1)    # broadcasting
        else:
            # generate random scores from uniform distribution
            # uniform_(0, 1): randomly select between 0 and 1
            scores = Variable(torch.Tensor(x.size(0), x.size(1), x.size(2)).uniform_(0, 1).cuda())
            weighted_features = x * scores

        decoded = self.vae(weighted_features)

        return scores, decoded
