import torch
import torch.nn as nn
from torch.autograd import Variable

import pdb

class cLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers = 2, bidirectional = False):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional

        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, bidirectional = bidirectional)

        #self.hidden_0 = self.init_hidden()
    """
    def init_hidden(self):
        return (Variable(torch.zeros(self.num_layers * 1, 1, self.hidden_size).cuda()),
                Variable(torch.zeros(self.num_layers * 1, 1, self.hidden_size).cuda()))
    """ 
    """
    Args:
        x: reconstructed (or original) video feature, (seq_len, 1, hidden_size) = (seq_len, 1, 2048)
    Return:
        h_last: the output of the last hidden (top) layer, (1, hidden_size) = (1, 2048) 
    """
    def forward(self, x):
        self.lstm.flatten_parameters()
        # h_n, h_c: shape (num_layers * 1, batch, hidden_size) = (2, 1, hidden_size)
        _, (h_n, h_c) = self.lstm(x)
        # get top layer
        h_last = h_n[-1]

        return h_last

class Discriminator(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers = 2):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.clstm = cLSTM(input_size, hidden_size, num_layers, False)
        self. mlp = nn.Sequential(nn.Linear(hidden_size, 1), nn.Sigmoid())

    """
    Args:
        x: reconstructed (or original) video feature, (seq_len, 1, hidden_size) = (seq_len, 1, 2048)
    Return:
        h: the output of the last hidden (top) layer, (1, hidden_size) = (1, 2048)
        prob: the discrimination result of cLSTM
    """
    def forward(self, x):
        # h: shape (1, hidden_size) = (1, 2048)
        h = self.clstm(x)

        #pdb.set_trace()
        # prob: a scalar
        prob = self.mlp(h).squeeze()

        return h, prob
