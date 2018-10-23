# Copyright 2018 Neural Networks and Deep Learning lab, MIPT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from typing import List, Union, Iterable

from deeppavlov.core.commands.utils import expand_path
from deeppavlov.core.common.log import get_logger
from deeppavlov.core.common.registry import register
from deeppavlov.core.models.component import Component
from deeppavlov.core.models.estimator import Estimator
from deeppavlov.core.data.utils import zero_pad_truncate

log = get_logger(__name__)


@register('ubuntu_v2_preprocessor')
class UbuntuV2Preprocessor(Estimator):
    """ Preprocessing of data samples containing few text strings to feed them in SMN or DAM ranking neural models.

    First ``num_context_turns`` strings in each data sample corresponds to the dialogue ``context``
    and the rest string(s) in the sample is (are) ``response(s)``.

    Args:
        save_path: The parameter is only needed to initialize the base class
            :class:`~deeppavlov.core.models.serializable.Serializable`.
        load_path: The parameter is only needed to initialize the base class
            :class:`~deeppavlov.core.models.serializable.Serializable`.
        max_sequence_length: A maximum length of text sequences in tokens.
            Longer sequences will be truncated and shorter ones will be padded.
        dynamic_batch:  Whether to use dynamic batching. If ``True``, the maximum length of a sequence for a batch
            will be equal to the maximum of all sequences lengths from this batch,
            but not higher than ``max_sequence_length``.
        padding: Padding. Possible values are ``pre`` and ``post``.
            If set to ``pre`` a sequence will be padded at the beginning.
            If set to ``post`` it will padded at the end.
        truncating: Truncating. Possible values are ``pre`` and ``post``.
            If set to ``pre`` a sequence will be truncated at the beginning.
            If set to ``post`` it will truncated at the end.
        num_context_turns: A number of ``context`` turns in data samples.
        num_ranking_samples: A number of condidates for ranking including positive one.
        tokenizer: An instance of one of the :class:`deeppavlov.models.tokenizers`.
        vocab: An instance of :class:`deeppavlov.core.data.simple_vocab.SimpleVocabulary`.
    """

    def __init__(self,
                 save_path: str,
                 load_path: str,
                 max_sequence_length: int = None,
                 dynamic_batch: bool = False,
                 padding: str = 'post',
                 truncating: str = 'post',
                 num_context_turns: int = 1,
                 num_ranking_samples: int = 1,
                 tokenizer: Component = None,
                 vocab: Estimator = "simple_vocab",
                 **kwargs):

        self.max_sequence_length = max_sequence_length
        self.padding = padding
        self.truncating = truncating
        self.dynamic_batch = dynamic_batch
        self.num_ranking_samples = num_ranking_samples
        self.num_context_turns = num_context_turns
        self.tokenizer = tokenizer
        self.vocab = vocab
        self.save_path = expand_path(save_path).resolve()
        self.load_path = expand_path(load_path).resolve()

        super().__init__(load_path=self.load_path, save_path=self.save_path, **kwargs)

    def destroy(self) -> None:
        pass

    def fit(self, x: List[List[str]]) -> None:
        x_tok = [self.tokenizer(el) for el in x]
        self.vocab.fit([el for x in x_tok for el in x])

    def __call__(self, x: Union[List[List[str]], List[str]]) -> Iterable[List[List[np.ndarray]]]:
        if len(x) == 0 or isinstance(x[0], str):
            if len(x) == 1:
                x_preproc = [el.split('&')for el in x]
            elif len(x) == 0:
                x_preproc = [['']]
            else:
                x_preproc = [[el] for el in x]
        else:
            x_preproc = [el[:self.num_context_turns+self.num_ranking_samples] for el in x]
        for el in x_preproc:
            x_tok = self.tokenizer(el)
            x_ctok = [y if len(y) != 0 else [''] for y in x_tok]
            x_proc = self.vocab(x_ctok)
            if self.dynamic_batch:
                msl = min((max([len(y) for el in x_tok for y in el]), self.max_sequence_length))
            else:
                msl = self.max_sequence_length
            x_proc = zero_pad_truncate(x_proc, msl, pad=self.padding, trunc=self.truncating)
            x_proc = list(x_proc)
            x_proc += el   # add (self.num_context_turns+self.num_ranking_samples) raw sentences
            # print(x_proc)
            yield x_proc

    def load(self) -> None:
        pass

    def save(self) -> None:
        self.vocab.save()
