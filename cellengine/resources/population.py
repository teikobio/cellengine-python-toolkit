from __future__ import annotations
from typing import Dict, Optional
from attr import define, field

import cellengine as ce
from cellengine.utils import converter
from cellengine.utils.readonly import readonly


@define
class Population:
    _id: str = field(on_setattr=readonly)
    experiment_id: str = field(on_setattr=readonly)
    name: str
    gates: str
    unique_name: Optional[str] = field(default=None, on_setattr=readonly)
    parent_id: Optional[str] = None
    terminal_gate_gid: Optional[str] = None

    def __repr__(self):
        return f"Population(_id='{self._id}', name='{self.name}')"

    @property
    def path(self):
        return f"experiments/{self.experiment_id}/populations/{self._id}".rstrip(
            "/None"
        )

    @classmethod
    def get(cls, experiment_id: str, _id: str = None, name: str = None) -> Population:
        """Get Population by name or ID for a specific experiment. Either
        `name` or `_id` must be specified.

        Args:
            experiment_id: ID of the experiment this attachment is connected with.
            _id (optional): ID of the attachment.
            name (optional): Name of the experiment.
        """
        kwargs = {"name": name} if name else {"_id": _id}
        return ce.APIClient().get_population(experiment_id, **kwargs)

    @classmethod
    def from_dict(cls, data: Dict):
        return converter.structure(data, cls)

    def to_dict(self) -> Dict:
        return converter.unstructure(self)

    def update(self):
        """Save changes to this Population to CellEngine."""
        res = ce.APIClient().update(self)
        self.__setstate__(res.__getstate__())  # type: ignore

    def delete(self):
        ce.APIClient().delete_entity(self.experiment_id, "populations", self._id)
