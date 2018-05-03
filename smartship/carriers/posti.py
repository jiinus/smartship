# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import deepcopy

import requests

from ..objects import (
    Agent, Locations, Parcels, PDFConfig, Receiver, Sender, SenderPartners,
    Service)
from ..shipments import Shipment

CARRIER_CODE = "POSTI"
CARRIER_DESCRIPTION = "Posti Oy, Paketit ja kuljetusyksiköt"

SERVICES = {
    "PO2017": "Posti - EMS",
    "PO2017D": "Posti - EMS DocPack",
    "ITKY14I": "Posti - Express Business Day pallet (Ulkomaa)",
    "IT14I": "Posti - Express Business Day parcel (Ulkomaa)",
    "PO2102": "Posti - Express-paketti",
    "PO2144": "Posti - Express-rahti",
    "PO2104": "Posti - Kotipaketti",
    "PO5041": "Posti - Näytelähetys",
    "PO2108": "Posti - Palautus",
    "PO2711": "Posti - Parcel Connect",
    "PO2718": "Posti - Parcel Return Connect",
    "PO2461": "Posti - Pikkupaketti",
    "PO2103": "Posti - Postipaketti",
    "ITPR": "Posti - Priority Parcel",
    "PO2106": "Posti - SmartPOST Viro",
}

NATIONAL_SERVICE_KEYS = [
    'ITPR',
    'PO2102',
    'PO2103',
    'PO2104',
    'PO2108',
    'PO2144',
    'PO2461',
    'PO5041',
]

NATIONAL_SERVICES = {
    key: description
    for (key, description) in SERVICES.items()
    if key in NATIONAL_SERVICE_KEYS
}

LOCATION_SERVICE_API_ENDPOINT = "https://locationservice.posti.com/location"


class MobileReceiver(Receiver):
    schema = deepcopy(Receiver.schema)
    schema["oneOf"][0] = {"required": ["name", "city", "country", "mobile"]}


class WeightedParcels(Parcels):
    schema = deepcopy(Parcels.schema)
    schema["items"]["required"].append("weight")


def create_shipment(
        custno, service_id, receiver, sender, parcels,
        agent=None, order_no=None, sender_reference=None, pdf_config=None, addons=None):
    """
    Create a shipment using the Posti carrier.

    Example simplest case usage:
        receiver = {
            "name": "Anders Innovations",
            "city": "Helsinki",
            "country": "FI",
            "address1": "Iso Roobertinkatu 20-22",
            "zipcode": "00120"
        }
        sender = {
            "quickId": "1",
        }
        shipment = create_shipment("12345", "PO2102", receiver, sender, [{"copies": 1}])

    :param custno: Posti customer number.
    :type custno: str
    :param service_id: Service to use, see `SERVICES` constant or API documentation.
    :type service_id: str
    :param receiver: Receiver of the shipment. Must either have a 'quickId' or enough address information.
        See example receiver data above. Required receiver information can depend on service chosen. If necessary,
        check service lists in Unifaun Online and API docs at https://smartship.unifaun.com/rs-docs/##creating_shipments
    :type receiver: dict
    :param parcels: Parcels to send in this shipment. This needs to be a list of items, with at minimum the amount
        of items in the parcel. For example, a shipment with one item:
            [
                {
                    "copies": 1,
                },
            ]
        See full specification of in the Smartship API documentation at
        https://smartship.unifaun.com/rs-docs/##creating_shipments
    :type parcels: list
    :param sender: Sender information. Must either have a 'quickId' or enough address information.
    :type sender: dict
    :param agent: Pickup agent (optional)
    :type agent: dict
    :param order_no: Order number (optional)
    :type order_no: str
    :param sender_reference: Sender reference (optional)
    :type sender_reference: str
    :param pdf_config: PDF config (optional)
    :type pdf_config: dict
    :param addons: Service addons. Available addons depend on chosen service (optional). See Unfifaun Online
        service lists. Defined as a list of dictionaries containing addon 'id' and additional information, for example:
            [
                {
                    "id": "DNG",
                    "declarant": "Firma Oy",
                },
                {
                    "id": "SPTR",
                },
            ]
    :type addons: list
    :return: Shipment instance
    :rtype: smartship.shipments.Shipment
    """
    _validate_create_shipment(service_id)
    receiver_class = _infer_receiver_class(service_id, agent)
    parcels_class = _infer_parcels_class(service_id)

    kwargs = {
        "sender": Sender(sender),
        "senderPartners": SenderPartners([{"id": CARRIER_CODE, "custNo": custno}]),
        "receiver": receiver_class(receiver),
        "parcels": parcels_class(parcels),
        "service": _build_service(addons, service_id),
    }
    if agent:
        kwargs["agent"] = Agent(agent)
    if order_no:
        kwargs["orderNo"] = order_no
    if sender_reference:
        kwargs["senderReference"] = sender_reference
    if pdf_config:
        kwargs["pdfConfig"] = PDFConfig(pdf_config)

    return Shipment(**kwargs)


def _build_service(addons, service_id):
    service = Service({"id": service_id})
    if addons:
        service["addons"] = addons
    return service


def _validate_create_shipment(service_id):
    if service_id not in SERVICES:
        raise ValueError("Invalid 'service_id'.")


def _infer_receiver_class(service_id, agent):
    if service_id == "PO2104":
        return MobileReceiver
    if service_id == "PO2103" and agent:
        return MobileReceiver
    return Receiver


def _infer_parcels_class(service_id):
    if service_id == "PO5041":
        return WeightedParcels
    return Parcels


def get_locations(
        country_code=None, top=None,
        types=None, lattitude=None, longitude=None, distance=None, bounding_box=None,
        zipcode=None, location_zipcode=None, strict_zip_code=None, city=None, municipality=None,
        pup_code=None, partner_type=None):
    """
    :param country_code: Limits results to given county. Default value is FI (Finland)
    :type country_code: str
    :param top: Amount of locations to return. API returns this amount of closest locations
    :type top: int
    :param types: supported location types are "POSTOFFICE", "LETTERBOX", "SMARTPOST", "PICKUPPOINT",
        "BUSINESSSERVICE", "POBOX", "LOCKER"
    :type types: list
    :param lattitude: Latitude of center location that search is done for. Top or distance parameter is required.
    :type lattitude: str
    :param : Longitude of center location that search is done for. Top or distance parameter is required.
    :type longitude: str
    :param distance: Filter which allows user to limit distance of returned locations. Parameter is used together with
        lattitude/longitude.
    :type distance: str
    :param bounding_box: Limits results to geographical bounding box.
    :type bounding_box: list
    :param zipcode: Filter results based on zipcode
    :type zipcode: str
    :param location_zipcode: Find the closest pickup points using zipcode
    :type location_zipcode: str
    :param strict_zip_code: This is used together with zip_code parameter. If this is set True only results that
        exactly match to the location zipcode are shown. If strict_zip_code is False, postal code area list is used to
        match location to queried zipcode. Default value is False.
    :type strict_zip_code: bool
    :param city: Filter results based on city. Matches to any language version of the city.
    :type city: str
    :param municipality: Filter results based on municipality. Matches to any language version of the municipality.
    :type municipality: str
    :param pup_code: Filter results based on PupCode
    :type pup_code: str
    :param partner_type: Filter results based on partner type. Allowed types: "POSTI", "AIBE", "BOXNET",
        "TOPO_CENTRAS".
    :type partner_type: str
    """
    params = {
        "countryCode": country_code,
        "top": top,
        "types": types,
        "lat": lattitude,
        "lng": longitude,
        "distance": distance,
        "zipCode": zipcode,
        "locationZipCode": location_zipcode,
        "strictZipCode": "true" if strict_zip_code else None,
        "city": city,
        "municipality": municipality,
        "pupCode": pup_code,
        "partnerType": partner_type,
    }

    if bounding_box is not None:
        params["topLeftLat"] = bounding_box[0]
        params["topLeftLng"] = bounding_box[1]
        params["bottomRightLat"] = bounding_box[2]
        params["bottomRightLng"] = bounding_box[3]

    for key, value in list(params.items()):
        if value is None:
            params.pop(key)

    response = requests.get(LOCATION_SERVICE_API_ENDPOINT, params=params)
    response.raise_for_status()
    return Locations(response.json()["locations"])
