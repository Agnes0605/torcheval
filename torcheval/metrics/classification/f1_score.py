# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# pyre-ignore-all-errors[16]: Undefined attribute of metric states.

from typing import Iterable, Optional, TypeVar

import torch

from torcheval.metrics.functional.classification.f1_score import (
    _f1_score_compute,
    _f1_score_param_check,
    _f1_score_update,
)
from torcheval.metrics.metric import Metric


TF1Score = TypeVar("TF1Score")


class MulticlassF1Score(Metric[torch.Tensor]):
    """
    Compute f1 score, which is defined as the harmonic mean of precision and recall.
    We convert NaN to zero when f1 score is NaN. This happens when either precision
    or recall is NaN or when both precision and recall are zero.
    Its functional version is ``torcheval.metrics.functional.multi_class_f1_score``.

    Args:
        num_classes:
            Number of classes.
        average:
            - ``'micro'``[default]:
                Calculate the metrics globally.
            - ``'macro'``:
                Calculate metrics for each class separately, and return their unweighted mean.
                Classes with 0 true and predicted instances are ignored.
            - ``'weighted'``"
                Calculate metrics for each class separately, and return their weighted sum.
                Weights are defined as the proportion of occurrences of each class in "target".
                Classes with 0 true and predicted instances are ignored.
            - ``None``:
                Calculate the metric for each class separately, and return
                the metric for every class.

    Example:
        >>> import torch
        >>> from torcheval.metrics import MulticlassF1Score
        >>> metric = MulticlassF1Score(num_classes=4)
        >>> input = torch.tensor([0, 2, 1, 3])
        >>> target = torch.tensor([0, 1, 2, 3])
        >>> metric.update(input, target)
        >>> metric.compute()
        tensor(0.5000)

        >>> metric = MulticlassF1Score(average=None, num_classes=4)
        >>> input = torch.tensor([0, 2, 1, 3])
        >>> target = torch.tensor([0, 1, 2, 3])
        >>> metric.update(input, target)
        >>> metric.compute()
        tensor([1., 0., 0., 1.])

        >>> metric = MulticlassF1Score(average="macro", num_classes=2)
        >>> input = torch.tensor([0, 0, 1, 1, 1])
        >>> target = torch.tensor([0, 0, 0, 0, 1])
        >>> metric.update(input, target)
        >>> metric.compute()
        tensor(0.5833)

        >>> metric = MulticlassF1Score(num_classes=4)
        >>> input = torch.tensor([[0.9, 0.1, 0, 0], [0.1, 0.2, 0.4, 0.3], [0, 1.0, 0, 0], [0, 0, 0.2, 0.8]])
        >>> target = torch.tensor([0, 1, 2, 3])
        >>> metric.update(input, target)
        >>> metric.compute()
        tensor(0.5)
    """

    def __init__(
        self: TF1Score,
        num_classes: Optional[int] = None,
        average: Optional[str] = "micro",
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__(device=device)
        _f1_score_param_check(num_classes, average)
        self.num_classes = num_classes
        self.average = average
        if average == "micro":
            self._add_state("num_tp", torch.tensor(0.0, device=self.device))
            self._add_state("num_label", torch.tensor(0.0, device=self.device))
            self._add_state(
                "num_prediction",
                torch.tensor(0.0, device=self.device),
            )
        else:
            # num_classes has been verified as a positive integer. Add this line to bypass pyre.
            assert isinstance(
                num_classes, int
            ), f"num_classes must be a integer, but got {num_classes}"

            self._add_state(
                "num_tp",
                torch.zeros(num_classes, device=self.device),
            )
            self._add_state(
                "num_label",
                torch.zeros(num_classes, device=self.device),
            )
            self._add_state(
                "num_prediction",
                torch.zeros(num_classes, device=self.device),
            )

    @torch.inference_mode()
    # pyre-ignore[14]: inconsistent override on *_:Any, **__:Any
    def update(self: TF1Score, input: torch.Tensor, target: torch.Tensor) -> TF1Score:
        """
        Update states with the ground truth labels and predictions.

        Args:
            input: Tensor of label predictions.
                It could be the predicted labels, with shape of (n_sample, ).
                It could also be probabilities or logits with shape of (n_sample, n_class).
                ``torch.argmax`` will be used to convert input into predicted labels.
            target: Tensor of ground truth labels with shape of (n_sample, ).
        """
        num_tp, num_label, num_prediction = _f1_score_update(
            input, target, self.num_classes, self.average
        )
        self.num_tp += num_tp
        self.num_label += num_label
        self.num_prediction += num_prediction
        return self

    @torch.inference_mode()
    def compute(self: TF1Score) -> torch.Tensor:
        """
        Return the f1 score.

        NaN is returned if no calls to ``update()`` are made before ``compute()`` is called.
        """
        return _f1_score_compute(
            self.num_tp, self.num_label, self.num_prediction, self.average
        )

    @torch.inference_mode()
    def merge_state(self: TF1Score, metrics: Iterable[TF1Score]) -> TF1Score:
        for metric in metrics:
            self.num_tp += metric.num_tp.to(self.device)
            self.num_label += metric.num_label.to(self.device)
            self.num_prediction += metric.num_prediction.to(self.device)
        return self
