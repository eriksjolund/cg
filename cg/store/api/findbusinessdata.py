"""Handler to find business data objects"""
import datetime as dt
from typing import List

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Query

from cg.store import models
from cg.store.api.base import BaseHandler


class FindBusinessDataHandler(BaseHandler):
    """Contains methods to find business data model instances"""

    def analyses(self, *, family: models.Family = None, before: dt.datetime = None) -> Query:
        """Fetch multiple analyses."""
        records = self.Analysis.query
        if family:
            query_family = family
            records = records.filter(models.Analysis.family == query_family)
        if before:
            subq = (
                self.Analysis.query.join(models.Analysis.family)
                .filter(models.Analysis.started_at < before)
                .group_by(models.Family.id)
                .with_entities(
                    models.Analysis.family_id,
                    func.max(models.Analysis.started_at).label("started_at"),
                )
                .subquery()
            )
            records = records.join(
                subq,
                and_(
                    self.Analysis.family_id == subq.c.family_id,
                    self.Analysis.started_at == subq.c.started_at,
                ),
            ).filter(models.Analysis.started_at < before)
        return records

    def latest_analyses(self) -> Query:
        """Fetch latest analysis for all cases."""

        records = self.Analysis.query
        sub_query = (
            self.Analysis.query.join(models.Analysis.family)
            .group_by(models.Family.id)
            .with_entities(
                models.Analysis.family_id, func.max(models.Analysis.started_at).label("started_at")
            )
            .subquery()
        )
        records = records.join(
            sub_query,
            and_(
                self.Analysis.family_id == sub_query.c.family_id,
                self.Analysis.started_at == sub_query.c.started_at,
            ),
        )
        return records

    def analysis(self, family: models.Family, started_at: dt.datetime) -> models.Analysis:
        """Fetch an analysis."""
        return self.Analysis.query.filter_by(family=family, started_at=started_at).first()

    def deliveries(self) -> Query:
        """Fetch all deliveries."""
        query = self.Delivery.query
        return query

    def families(
        self, *, customer: models.Customer = None, enquiry: str = None, action: str = None,
    ) -> List[models.Family]:
        """Fetch families."""
        records = self.Family.query
        records = records.filter_by(customer=customer) if customer else records

        records = (
            records.filter(
                or_(
                    models.Family.name.like(f"%{enquiry}%"),
                    models.Family.internal_id.like(f"%{enquiry}%"),
                )
            )
            if enquiry
            else records
        )

        records = records.filter_by(action=action) if action else records

        return records.order_by(models.Family.created_at.desc())

    def families_in_customer_group(
        self, *, customer: models.Customer = None, enquiry: str = None
    ) -> List[models.Family]:
        """Fetch all families including those from collaborating customers."""
        records = self.Family.query.join(models.Family.customer, models.Customer.customer_group)

        if customer:
            records = records.filter(models.CustomerGroup.id == customer.customer_group_id)

        records = (
            records.filter(
                or_(
                    models.Family.name.like(f"%{enquiry}%"),
                    models.Family.internal_id.like(f"%{enquiry}%"),
                )
            )
            if enquiry
            else records
        )

        return records.order_by(models.Family.created_at.desc())

    def family(self, internal_id: str) -> models.Family:
        """Fetch a family by internal id from the database."""
        return self.Family.query.filter_by(internal_id=internal_id).first()

    def family_samples(self, family_id: str) -> List[models.FamilySample]:
        """Find the samples of a family."""
        return (
            self.FamilySample.query.join(models.FamilySample.family, models.FamilySample.sample)
            .filter(models.Family.internal_id == family_id)
            .all()
        )

    def find_family(self, customer: models.Customer, name: str) -> models.Family:
        """Find a family by family name within a customer."""
        return self.Family.query.filter_by(customer=customer, name=name).first()

    def find_sample(self, customer: models.Customer, name: str) -> List[models.Sample]:
        """Find samples within a customer."""
        return self.Sample.query.filter_by(customer=customer, name=name)

    def find_sample_in_customer_group(
        self, customer: models.Customer, name: str
    ) -> List[models.Sample]:
        """Find samples within the customer group."""
        return self.Sample.query.filter(
            models.Sample.customer.customer_group == customer.customer_group, name == name,
        )

    def flowcell(self, name: str) -> models.Flowcell:
        """Fetch a flowcell."""
        return self.Flowcell.query.filter_by(name=name).first()

    def flowcells(
        self, *, status: str = None, family: models.Family = None, enquiry: str = None
    ) -> Query:
        """Fetch all flowcells."""
        records = self.Flowcell.query
        if family:
            records = records.join(models.Flowcell.samples, models.Sample.links).filter(
                models.FamilySample.family == family
            )
        if status:
            records = records.filter_by(status=status)
        if enquiry:
            records = records.filter(models.Flowcell.name.like(f"%{enquiry}%"))
        return records.order_by(models.Flowcell.sequenced_at.desc())

    def invoices(self, invoiced: bool = None) -> Query:
        """Fetch invoices."""
        query = self.Invoice.query
        if invoiced is True:
            query = query.filter(models.Invoice.invoiced_at != None)
        elif invoiced is False:
            query = query.filter(models.Invoice.invoiced_at == None)
        return query

    def invoice(self, invoice_id: int) -> models.Invoice:
        """Fetch an invoice."""
        return self.Invoice.get(invoice_id)

    def invoice_samples(self, *, invoice_id: int = None) -> List[models.Sample]:
        """Fetch pools and samples for an invoice"""
        pools = self.Pool.query.filter_by(invoice_id=invoice_id).all()
        samples = self.Sample.query.filter_by(invoice_id=invoice_id).all()
        return pools + samples

    def link(self, family_id: str, sample_id: str) -> models.FamilySample:
        """Find a link between a family and a sample."""
        return (
            self.FamilySample.query.join(models.FamilySample.family, models.FamilySample.sample)
            .filter(models.Family.internal_id == family_id, models.Sample.internal_id == sample_id,)
            .first()
        )

    def microbial_order(self, internal_id: str) -> models.MicrobialOrder:
        """Fetch an order by internal id from the database."""
        return self.MicrobialOrder.query.filter_by(internal_id=internal_id).first()

    def microbial_orders(
        self, *, customer: models.Customer = None, enquiry: str = None
    ) -> List[models.MicrobialOrder]:
        """Fetch all microbial_orders."""
        records = self.MicrobialOrder.query
        records = records.filter_by(customer=customer) if customer else records
        records = (
            records.filter(
                or_(
                    models.MicrobialOrder.name.like(f"%{enquiry}%"),
                    models.MicrobialOrder.internal_id.like(f"%{enquiry}%"),
                )
            )
            if enquiry
            else records
        )
        return records.order_by(models.MicrobialOrder.created_at.desc())

    def microbial_samples(
        self, *, customer: models.Customer = None, enquiry: str = None
    ) -> List[models.MicrobialSample]:
        records = self.MicrobialSample.query

        if customer:
            records.join(models.MicrobialOrder)
            records = records.filter_by(models.MicrobialOrder.customer == customer)

        records = (
            records.filter(
                or_(
                    models.MicrobialSample.name.like(f"%{enquiry}%"),
                    models.MicrobialSample.internal_id.like(f"%{enquiry}%"),
                )
            )
            if enquiry
            else records
        )

        return records.order_by(models.MicrobialSample.created_at.desc())

    def microbial_sample(self, internal_id: str) -> models.MicrobialSample:
        """Fetch a microbial sample by lims id."""
        return self.MicrobialSample.query.filter_by(internal_id=internal_id).first()

    def new_invoice_id(self) -> Query:
        """Fetch invoices."""
        query = self.Invoice.query.all()
        ids = [inv.id for inv in query]
        if ids:
            new_id = max(ids) + 1
        else:
            new_id = 0
        return new_id

    def pools(self, *, customer: models.Customer, enquiry: str = None) -> Query:
        """Fetch all the pools for a customer."""
        records = self.Pool.query
        records = records.filter_by(customer=customer) if customer else records

        records = (
            records.filter(
                or_(models.Pool.name.like(f"%{enquiry}%"), models.Pool.order.like(f"%{enquiry}%"),)
            )
            if enquiry
            else records
        )

        return records.order_by(models.Pool.created_at.desc())

    def pool(self, pool_id: int):
        """Fetch a pool."""
        return self.Pool.get(pool_id)

    def sample(self, internal_id: str) -> models.Sample:
        """Fetch a sample by lims id."""
        return self.Sample.query.filter_by(internal_id=internal_id).first()

    def samples(
        self, *, customer: models.Customer = None, enquiry: str = None
    ) -> List[models.Sample]:
        records = self.Sample.query
        records = records.filter_by(customer=customer) if customer else records
        records = (
            records.filter(
                or_(
                    models.Sample.name.like(f"%{enquiry}%"),
                    models.Sample.internal_id.like(f"%{enquiry}%"),
                )
            )
            if enquiry
            else records
        )
        return records.order_by(models.Sample.created_at.desc())

    def samples_by_ids(self, **identifiers) -> List[models.Sample]:
        records = self.Sample.query

        for identifier_name, identifier_value in identifiers.items():
            identifier = getattr(models.Sample, identifier_name)
            records = records.filter(identifier.contains(identifier_value))

        return records.order_by(models.Sample.internal_id.asc())

    def samples_in_customer_group(
        self, *, customer: models.Customer = None, enquiry: str = None
    ) -> List[models.Sample]:
        """Fetch all samples including those from collaborating customers."""

        records = self.Sample.query.join(models.Sample.customer, models.Customer.customer_group)

        if customer:
            records = records.filter(models.CustomerGroup.id == customer.customer_group_id)

        records = (
            records.filter(
                or_(
                    models.Sample.name.like(f"%{enquiry}%"),
                    models.Sample.internal_id.like(f"%{enquiry}%"),
                )
            )
            if enquiry
            else records
        )
        return records.order_by(models.Sample.created_at.desc())
