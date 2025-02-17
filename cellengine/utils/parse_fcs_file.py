import flowio
from pandas import DataFrame
import numpy as np
from typing import BinaryIO, Union


def parse_fcs_file(file: Union[BinaryIO, str]) -> DataFrame:
    data = flowio.FlowData(file, True)
    events = np.reshape(data.events, (-1, data.channel_count))  # type: ignore
    channels = sorted(data.channels.items(), key=lambda k: int(k[0]))
    pnn = [k[1]["PnN"] for k in channels]
    pns = [k[1].get("PnS") for k in channels]
    return DataFrame(events, columns=[pnn, pns], dtype="float32")
