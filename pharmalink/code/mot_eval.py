"""Module for storing and accessing probability data for different modes of transportation.

The probabilities are calculated from the "Mobilität in Tabellen (MiT 2017)" dataset.
For detailed information see thesis/Quellen/mit-output-preprocessing.ipynb.

Classes:
    MOTProbs

Functions:
    None

Attributes:
    PROBS: Dictionary to create the probability DataFrame from.
"""

import json
import pandas as pd
from typing import List


class MOTEvaluator:
    """Class dealing with probability data for different modes of transportation."""

    # Probabilities calculated from the "Mobilität in Tabellen (MiT 2017)" dataset.
    # For detailed information see thesis/Quellen/MobilitätInTabellen2017/mit-output-preprocessing.ipynb.
    DATA = """{
        "breaks": [
            0,
            0.5,
            1,
            2,
            5,
            10,
            20,
            50,
            100,
            "Infinity"
        ],
        "probs": [
            {
                "auto": 0.12371134020618557,
                "bicycle": 0.09278350515463918,
                "pedestrian": 0.7835051546391752
            },
            {
                "auto": 0.3010752688172043,
                "bicycle": 0.1827956989247312,
                "pedestrian": 0.5161290322580645
            },
            {
                "auto": 0.47727272727272724,
                "bicycle": 0.2159090909090909,
                "pedestrian": 0.3068181818181818
            },
            {
                "auto": 0.6790123456790124,
                "bicycle": 0.16049382716049382,
                "pedestrian": 0.16049382716049382
            },
            {
                "auto": 0.8552631578947368,
                "bicycle": 0.09210526315789475,
                "pedestrian": 0.05263157894736842
            },
            {
                "auto": 0.948051948051948,
                "bicycle": 0.03896103896103895,
                "pedestrian": 0.012987012987012984
            },
            {
                "auto": 0.961038961038961,
                "bicycle": 0.025974025974025972,
                "pedestrian": 0.012987012987012986
            },
            {
                "auto": 0.9726027397260274,
                "bicycle": 0.027397260273972605,
                "pedestrian": 0.0
            },
            {
                "auto": 1.0,
                "bicycle": 0.0,
                "pedestrian": 0.0
            }
        ]
    }"""

    __slots__ = ["_probabilities"]

    def __init__(self) -> None:
        """Initialize the class and create the probability DataFrame."""

        data = json.loads(self.DATA)

        # Replace "Infinity" with float("inf") to make it a valid numeric value
        if isinstance(data["breaks"][-1], str):
            data["breaks"][-1] = float("inf")

        index = pd.IntervalIndex.from_breaks(
            data["breaks"], closed="left", name="distance"
        )

        probs = pd.DataFrame(data["probs"], index=index)

        self._probabilities = probs

    @property
    def probabilities(self) -> pd.DataFrame:
        """Return the probability DataFrame.

        Returns:
            pd.DataFrame: The probability DataFrame.
        """

        return self._probabilities

    @probabilities.setter
    def probabilities(self, value) -> None:
        """Protect probabilities from being changed and warn user."""
        raise AttributeError(
            f"Probabilities must not be changed, change values in DATA constant in class definition instead."
        )

    @probabilities.deleter
    def probabilities(self) -> None:
        """Protect probabilities from being deleted and warn user."""
        raise AttributeError(
            f"Probabilities must not be deleted, change values in DATA constant in class definition instead."
        )

    def evaluate_mot(self, distance: float, choices: List[str]) -> str:
        """Return a suitable mode of transportation for a given distance.

        Returns either "auto", "bicycle" or "pedestrian" with probabilities
        based on the given distance.

        Args:
            distance (float): The distance.
            choices (List[str]): The modes of transportation to choose from.

        Returns:
            str: The mode of transportation.
        """

        # Get the probability table
        table = self.probabilities

        # Find the row with the interval that contains the given distance
        row = table.loc[distance]

        # Filter the row to only include the given choices
        row = row[choices]

        # Draw a mode of transportation with the probabilities from the row
        draw = row.sample(1, weights=row.values).index[0]

        return draw
