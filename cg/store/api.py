# -*- coding: utf-8 -*-
import datetime as dt
import logging
from typing import List

import alchy
import petname

from cg.constants import PRIORITY_MAP
from cg.exc import MissingCustomerError
from . import models

log = logging.getLogger(__name__)


class BaseHandler:

    User = models.User
    Customer = models.Customer
    Sample = models.Sample
    Family = models.Family
    FamilySample = models.FamilySample
    Flowcell = models.Flowcell
    Analysis = models.Analysis

    def customer(self, internal_id: str) -> models.Customer:
        """Fetch a customer by internal id from the store."""
        return self.Customer.query.filter_by(internal_id=internal_id).first()

    def family(self, internal_id: str) -> models.Family:
        """Fetch a family by internal id from the database."""
        return self.Family.query.filter_by(internal_id=internal_id).first()

    def sample(self, internal_id: str) -> models.Sample:
        """Fetch a sample by lims id."""
        return self.Sample.query.filter_by(internal_id=internal_id).first()

    def find_family(self, customer: models.Customer, name: str) -> models.Family:
        """Find a family by family name within a customer."""
        return self.Family.query.filter_by(customer=customer, name=name).first()

    def add_customer(self, internal_id: str, name: str) -> models.Customer:
        """Add a new customer to the database."""
        new_customer = self.Customer(internal_id=internal_id, name=name)
        return new_customer

    def add_user(self, customer: models.Customer, name: str, email: str,
                 admin: bool=False) -> models.User:
        """Add a new user to the database."""
        new_user = self.User(customer=customer, name=name, email=email, is_admin=admin)
        return new_user

    def add_sample(self, customer: models.Customer, name: str, sex: str, internal_id: str=None,
                   received: dt.datetime=None, external: bool=False) -> models.Sample:
        """Add a new sample to the database."""
        if internal_id is None:
            # generate a unique sample id
            while True:
                internal_id = petname.Generate(3, separator='')
                if self.sample(internal_id) is None:
                    break
                else:
                    log.debug(f"{internal_id} already used - trying another id")
        new_sample = self.Sample(customer=customer, name=name, internal_id=internal_id,
                                 received_at=received, is_external=external, sex=sex)
        return new_sample

    def add_family(self, customer: models.Customer, name: str, panels: List[str],
                   priority: str='standard') -> models.Family:
        """Add a new family to the database."""
        # generate a unique family id
        while True:
            internal_id = petname.Generate(2, separator='')
            if self.family(internal_id) is None:
                break
            else:
                log.debug(f"{internal_id} already used - trying another id")

        new_family = self.Family(customer=customer, internal_id=internal_id, name=name,
                                 priority=PRIORITY_MAP[priority])
        new_family.panels = panels
        return new_family

    def relate_sample(self, family: models.Family, sample: models.Sample,
                      status: str, mother: models.Sample=None,
                      father: models.Sample=None) -> models.FamilySample:
        """Relate a sample to a family."""
        new_record = self.FamilySample(family=family, sample=sample, status=status,
                                       mother=mother, father=father)
        return new_record

    def add_flowcell(self, name: str, sequencer: str, sequenced: dt.datetime,
                     samples: List[models.Sample]) -> models.Flowcell:
        new_record = self.Flowcell(name=name, sequencer_type=sequencer, sequenced_at=sequenced,
                                   samples=samples)
        return new_record

    def add_analysis(self, family: models.Family, pipeline: str, version: str,
                     analyzed: dt.datetime, primary: bool=False) -> models.Analysis:
        """Add a new analysis to the database."""
        new_record = self.Analysis(family=family, pipeline=pipeline, pipeline_version=version,
                                   analyzed_at=analyzed, is_primary=primary)
        return new_record

    def add_order(self, data: dict) -> List[models.Family]:
        """Add a new order of samples to the database."""
        records = []
        for family in data['families']:
            customer_obj = self.customer(data['customer'])
            if customer_obj is None:
                raise MissingCustomerError(f"can't find customer: {data['customer']}")

            family_obj = self.add_family(customer_obj, family['name'], family['panels'],
                                         priority=family['priority'])
            self.add(family_obj)

            for sample in family['samples']:
                sample_obj = self.add_sample(customer_obj, family_obj, id=sample['id'],
                                             name=sample['name'], external=sample.get('external'))
                self.add(sample_obj)

            records.append(family_obj)
        return records


class Store(alchy.Manager, BaseHandler):

    def __init__(self, uri):
        super(Store, self).__init__(config=dict(SQLALCHEMY_DATABASE_URI=uri), Model=models.Model)
