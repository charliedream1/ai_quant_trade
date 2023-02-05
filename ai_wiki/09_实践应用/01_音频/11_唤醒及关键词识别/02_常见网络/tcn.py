#!/usr/bin/env python3
# Copyright (c) 2021 Binbin Zhang
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class CnnBlock(nn.Module):
    def __init__(self,
                 channel: int,
                 kernel_size: int,
                 dilation: int,
                 dropout: float = 0.1):
        super().__init__()
        # The CNN used here is causal convolution
        self.padding = (kernel_size - 1) * dilation
        self.cnn = nn.Conv1d(channel,
                             channel,
                             kernel_size,
                             stride=1,
                             dilation=dilation)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, cache: Optional[torch.Tensor] = None):
        """
        Args:
            x(torch.Tensor): Input tensor (B, D, T)
        Returns:
            torch.Tensor(B, D, T)
        """
        if cache is None:
            y = F.pad(x, (self.padding, 0), value=0.0)
        else:
            y = torch.cat((cache, x), dim=2)
        assert y.size(2) > self.padding
        new_cache = y[:, :, -self.padding:]

        y = self.cnn(y)
        y = F.relu(y)
        y = self.dropout(y)
        y = y + x  # residual connection
        return y, new_cache


class DsCnnBlock(nn.Module):
    """ Depthwise Separable Convolution
    """
    def __init__(self,
                 channel: int,
                 kernel_size: int,
                 dilation: int,
                 dropout: float = 0.1):
        super().__init__()
        # The CNN used here is causal convolution
        self.padding = (kernel_size - 1) * dilation
        self.depthwise_cnn = nn.Conv1d(channel,
                                       channel,
                                       kernel_size,
                                       stride=1,
                                       dilation=dilation,
                                       groups=channel)
        self.pointwise_cnn = nn.Conv1d(channel,
                                       channel,
                                       kernel_size=1,
                                       stride=1)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, cache: Optional[torch.Tensor] = None):
        """
        Args:
            x(torch.Tensor): Input tensor (B, D, T)
        Returns:
            torch.Tensor(B, D, T)
        """
        if cache is None:
            y = F.pad(x, (self.padding, 0), value=0.0)
        else:
            y = torch.cat((cache, x), dim=2)
        assert y.size(2) > self.padding
        new_cache = y[:, :, -self.padding:]

        y = self.depthwise_cnn(y)
        y = self.pointwise_cnn(y)
        y = F.relu(y)
        y = self.dropout(y)
        y = y + x  # residual connection
        return y, new_cache


class TCN(nn.Module):
    def __init__(self,
                 num_layers: int,
                 channel: int,
                 kernel_size: int,
                 dropout: float = 0.1,
                 block_class=CnnBlock):
        super().__init__()
        layers = []
        self.padding = 0
        self.network = nn.ModuleList()
        for i in range(num_layers):
            dilation = 2**i
            self.padding += (kernel_size - 1) * dilation
            self.network.append(
                block_class(channel, kernel_size, dilation, dropout))

    def forward(self, x: torch.Tensor, cache: Optional[torch.Tensor] = None):
        """
        Args:
            x (torch.Tensor): Input tensor (B, T, D)

        Returns:
            torch.Tensor(B, T, D)
            torch.Tensor(B, D, C): C is the accumulated cache size
        """
        x = x.transpose(1, 2)  # (B, D, T)
        out_caches = []
        for block in self.network:
            x, c = block(x)
            out_caches.append(c)
        x = x.transpose(1, 2)  # (B, T, D)
        new_cache = torch.cat(out_caches, dim=2)
        return x, new_cache


if __name__ == '__main__':
    tcn = TCN(4, 64, 8, block_class=CnnBlock)
    print(tcn)
    print(tcn.padding)
    num_params = sum(p.numel() for p in tcn.parameters())
    print('the number of model params: {}'.format(num_params))
    x = torch.zeros(3, 15, 64)
    y = tcn(x)

    from torchinfo import summary
    summary(tcn, input_size=[(3, 15, 64)])
