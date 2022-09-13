import os
import sys
import json
import boto3
import urllib3
from datetime import date, datetime
import time
import logging

LOGGER = logging.getLogger()
if 'log_level' in os.environ:
    LOGGER.setLevel(os.environ['log_level'])
    print('Log level set to %s' % LOGGER.getEffectiveLevel())
else:
    LOGGER.setLevel(logging.ERROR)

session = boto3.Session()

# environment variables
# EGRESS_TGW_ROUTETABLE = 'Egress-RTB'

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError('Type %s not serializable' % type(obj))

def send_response(event, context, responseStatus, responseData, physicalResourceId=None,noEcho=False):
    responseUrl = event['ResponseURL']
    ls = context.log_stream_name
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'View details in Log Stream: '+ls
    responseBody['PhysicalResourceId'] = physicalResourceId or ls
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = responseData
    jsonResponseBody = json.dumps(responseBody)
    print('ResponseBody: \n'+jsonResponseBody)
    headers = {
        'content-type': '',
        'content-length': str(len(jsonResponseBody))
    }
    http = urllib3.PoolManager()
    try:
        response = http.request('PUT', responseUrl, body=jsonResponseBody, headers=headers)
        print('StatusCode = '+response.reason)
    except Exception as e:
        print(f'send_response(..) failed executing requests.put(..): {e}')

def create_vpc_route(ec2_client, member_cidr, tgw_id, rtb_id):
    try:
        ec2_client.create_route(
            DestinationCidrBlock=member_cidr,
            TransitGatewayId=tgw_id,
            RouteTableId=rtb_id
        )
        print('Route added for Cidr: {} in RouteTable: {}'.format(member_cidr, rtb_id))
    except Exception as e:
        LOGGER.error(f'failed in create_route(..): {e}')
        LOGGER.error(str(e))
        raise e

def add_routes(ec2_client, member_cidr, vpc_id, subnet_id, tgw_id):
    return_rtb_ids = []
    try:
        if subnet_id == None:
            rtb_ids = get_rtbs(ec2_client, vpc_id)
            for rtb_id in rtb_ids:
                create_vpc_route(ec2_client, member_cidr, tgw_id, rtb_id)
                return_rtb_ids.append(rtb_id)
        else:
            vpc_rtb_id = get_rtb(ec2_client, vpc_id, subnet_id)
            create_vpc_route(ec2_client, member_cidr, tgw_id, vpc_rtb_id)
            return_rtb_ids.append(vpc_rtb_id)
        return return_rtb_ids
    except Exception as e:
        LOGGER.error(f'failed in add_routes(..): {e}')
        LOGGER.error(str(e))
        raise e

def delete_routes(ec2_client, member_cidr, vpc_id, subnet_id):
    return_rtb_ids = []
    try:
        if subnet_id == None:
            rtb_ids = get_rtbs(ec2_client, vpc_id)
            for rtb_id in rtb_ids:
                ec2_client.delete_route(
                    DestinationCidrBlock=member_cidr,
                    RouteTableId=rtb_id
                )
                print('Route deleted for Cidr: {} in RouteTable: {}'.format(member_cidr, rtb_id))
                return_rtb_ids.append(rtb_id)
        else:
            vpc_rtb_id = get_rtb(ec2_client, vpc_id, subnet_id)
            ec2_client.delete_route(
                DestinationCidrBlock=member_cidr,
                RouteTableId=vpc_rtb_id
            )
            print('Route deleted for Cidr: {} in RouteTable: {}'.format(member_cidr, vpc_rtb_id))
            return_rtb_ids.append(vpc_rtb_id)
        return return_rtb_ids
    except Exception as e:
        LOGGER.error(f'failed in delete_routes(..): {e}')
        LOGGER.error(str(e))
        raise e

def get_rtbs(ec2_client, vpc_id):
    filters = []
    mainFilter = {
        'Name': 'association.main',
        'Values': [ 'false' ]
    }
    vpcFilter = {
        'Name': 'vpc-id',
        'Values': [ vpc_id ]
    }
    filters.append(mainFilter)
    filters.append(vpcFilter)
    rtb_ids = []
    try:
        response = ec2_client.describe_route_tables(
            Filters=filters
        )
        if 'RouteTables' in response:
            for routeTable in response['RouteTables']:
                rtb_ids.append(routeTable['RouteTableId'])
            return rtb_ids
    except Exception as e:
        LOGGER.error(f'failed in describe_route_tables(..): {e}')
        LOGGER.error(str(e))
        raise e

def get_rtb(ec2_client, vpc_id, subnet_id):
    filters = []
    mainFilter = {
        'Name': 'association.main',
        'Values': [ 'false' ]
    }
    vpcFilter = {
        'Name': 'vpc-id',
        'Values':  [ vpc_id ]
    }
    subnetFilter = {
        'Name': 'association.subnet-id',
        'Values': [ subnet_id ]
    }
    filters.append(mainFilter)
    filters.append(vpcFilter)
    filters.append(subnetFilter)
    try:
        response = ec2_client.describe_route_tables(
            Filters=filters
        )
        if 'RouteTables' in response:
            return response['RouteTables'][0]['RouteTableId']
    except Exception as e:
        LOGGER.error(f'failed in describe_route_tables(..): {e}')
        LOGGER.error(str(e))
        raise e

def propagate_tgw_route(ec2_client, member_account, member_vpc_id, tgw_rtb_name):
    try:
        tgw_rtb_id = get_tgw_rtb_id(ec2_client, tgw_rtb_name)
        tgw_attach_id = get_tgw_attachment(ec2_client, member_account, member_vpc_id)
        ec2_client.enable_transit_gateway_route_table_propagation(
            TransitGatewayRouteTableId=tgw_rtb_id,
            TransitGatewayAttachmentId=tgw_attach_id
        )
        print('Route for TGW Attachment: {} of VPC: {} propagated to RouteTable: {}'.format(tgw_attach_id, member_vpc_id, tgw_rtb_id))
        return tgw_rtb_id
    except Exception as e:
        LOGGER.error(f'failed in enable_transit_gateway_route_table_propagation(..): {e}')
        LOGGER.error(str(e))
        raise e

def unpropagate_tgw_route(ec2_client, member_account, member_vpc_id, tgw_rtb_name):
    try:
        tgw_rtb_id = get_tgw_rtb_id(ec2_client, tgw_rtb_name)
        tgw_attach_id = get_tgw_attachment(ec2_client, member_account, member_vpc_id)
        ec2_client.disable_transit_gateway_route_table_propagation(
            TransitGatewayRouteTableId=tgw_rtb_id,
            TransitGatewayAttachmentId=tgw_attach_id
        )
        print('Route for TGW Attachment: {} of VPC: {} unpropagated from RouteTable: {}'.format(tgw_attach_id, member_vpc_id, tgw_rtb_id))
        return tgw_rtb_id
    except Exception as e:
        LOGGER.error(f'failed in disable_transit_gateway_route_table_propagation(..): {e}')
        LOGGER.error(str(e))
        raise e

def add_tgw_static_route(ec2_client, event):
    tgw_rtb_name = os.environ['EGRESS_TGW_ROUTETABLE']
    resProps = event['ResourceProperties']
    member_account = resProps['member_account']
    member_vpc_id = resProps['member_vpc_id']
    member_cidr = resProps['member_cidr']
    tgw_id = resProps['tgw_id']
    egress_rtb_id = ''
    try:
        rtb_id = get_tgw_rtb_id(ec2_client, tgw_rtb_name)
        if rtb_id != '':
            egress_rtb_id = rtb_id
        else:
            egress_rtb_id = create_egress_tgw_rtb(ec2_client, tgw_id)
        tgw_attach_id = get_tgw_attachment(ec2_client, member_account, member_vpc_id)
        ec2_client.create_transit_gateway_route( 
            DestinationCidrBlock=member_cidr,
            TransitGatewayRouteTableId=egress_rtb_id,
            TransitGatewayAttachmentId=tgw_attach_id
        )
        print('Member Cidr: {} added to TGW RouteTable Id: {}'.format(member_cidr, egress_rtb_id))
        return egress_rtb_id
    except Exception as e:
        LOGGER.error(f'failed in create_transit_gateway_route(..): {e}')
        LOGGER.error(str(e))
        raise e

def delete_tgw_static_route(ec2_client, member_cidr):
    tgw_rtb_name = os.environ['EGRESS_TGW_ROUTETABLE']
    try:
        egress_rtb_id = get_tgw_rtb_id(ec2_client, tgw_rtb_name)
        ec2_client.delete_transit_gateway_route(
            TransitGatewayRouteTableId=egress_rtb_id,
            DestinationCidrBlock=member_cidr
        )
        print('Member Cidr: {} added to TGW RouteTable Id: {}'.format(member_cidr, egress_rtb_id))
        return egress_rtb_id
    except Exception as e:
        LOGGER.error(f'failed in delete_transit_gateway_route(..): {e}')
        LOGGER.error(str(e))
        raise e

def get_tgw_rtb_id(ec2_client, tgw_rtb_name):
    tgw_rtb_id = ''
    filters = []
    nameFilter = {
        'Name': 'tag:Name',
        'Values': [ tgw_rtb_name ]
    }
    filters.append(nameFilter)
    try:
        response = ec2_client.describe_transit_gateway_route_tables(
            Filters=filters
        )
        if 'TransitGatewayRouteTables' in response:
            if len(response['TransitGatewayRouteTables']) == 1:
                tgw_rtb_id = response['TransitGatewayRouteTables'][0]['TransitGatewayRouteTableId']
    except Exception as e:
        LOGGER.error(f'failed in describe_transit_gateway_route_tables(..): {e}')
        LOGGER.error(str(e))
        raise e
    return tgw_rtb_id

def create_egress_tgw_rtb(ec2_client, tgw_id):
    tags = []
    nameTag = {
        'Key': 'Name',
        'Value': os.environ['EGRESS_TGW_ROUTETABLE']
    }
    tags.append(nameTag)
    try:
        response = ec2_client.create_transit_gateway_route_table(
            TransitGatewayId=tgw_id,
            Tags=tags
        )
        egress_rtb_id = response['TransitGatewayRouteTable']['TransitGatewayRouteTableId']
        print('TGW RouteTable created with Id: {}'.format(egress_rtb_id))
        return egress_rtb_id
    except Exception as e:
        LOGGER.error(f'failed in create_transit_gateway_route_table(..): {e}')
        LOGGER.error(str(e))
        raise e

def get_tgw_attachment(ec2_client, member_account, member_vpc_id):
    filters = []
    resOwnerFilter = {
        'Name': 'resource-owner-id',
        'Values': [ member_account ]
    }
    resIdFilter = {
        'Name': 'resource-id',
        'Values': [ member_vpc_id ]
    }
    filters.append(resOwnerFilter)
    filters.append(resIdFilter)
    try:
        response = ec2_client.describe_transit_gateway_attachments(
            Filters=filters
        )
        if 'TransitGatewayAttachments' in response:
            tgwAttachId = response['TransitGatewayAttachments'][0]['TransitGatewayAttachmentId']
            print('Return TGW Attachment Id: {}'.format(tgwAttachId))
            return tgwAttachId
    except Exception as e:
        LOGGER.error(f'failed in describe_transit_gateway_attachments(..): {e}')
        LOGGER.error(str(e))

def create_operation(event, context):
    try:
        resProps = event['ResourceProperties']
        member_account = resProps['member_account']
        member_region = resProps['member_region']
        member_vpc_id = resProps['member_vpc_id']
        member_cidr = resProps['member_cidr']
        hub_intern_vpc_id = resProps['hub_intern_vpc_id']
        hub_intern_subnet_id = resProps['hub_intern_subnet_id']
        hub_egress_vpc_id = resProps['hub_egress_vpc_id']
        tgw_id = resProps['tgw_id']
        ec2_client = session.client('ec2')
        # add egress vpc routes
        egress_rtb_ids = add_routes(ec2_client, member_cidr, hub_egress_vpc_id, None, tgw_id)
        # add internal vpc routes
        intern_rtb_ids = add_routes(ec2_client, member_cidr, hub_intern_vpc_id, hub_intern_subnet_id, tgw_id)
        # create route propagation for member vpc in 'Egress-RTB' TGW RTB
        tgw_rtb_id = propagate_tgw_route(ec2_client, member_account, member_vpc_id, os.environ['EGRESS_TGW_ROUTETABLE'])
        responseData = {
            'member_account': member_account,
            'member_region': member_region,
            'member_vpc_id': member_vpc_id,
            'member_cidr': member_cidr,
            'hub_intern_rtb_ids': intern_rtb_ids,
            'hub_egress_rtb_ids': egress_rtb_ids,
            'egress_rtb_id': tgw_rtb_id
        }
        send_response(event, context, 'SUCCESS', responseData)
    except Exception as e:
        LOGGER.error(f'failed in create_operation(..): {e}')
        LOGGER.error(str(e))
        responseData = {
            'exc_info': str(e)
        }
        send_response(event, context, 'FAILED', responseData)

def delete_operation(event, context):
    try:
        resProps = event['ResourceProperties']
        member_account = resProps['member_account']
        member_region = resProps['member_region']
        member_vpc_id = resProps['member_vpc_id']
        member_cidr = resProps['member_cidr']
        hub_intern_vpc_id = resProps['hub_intern_vpc_id']
        hub_intern_subnet_id = resProps['hub_intern_subnet_id']
        hub_egress_vpc_id = resProps['hub_egress_vpc_id']
        tgw_id = resProps['tgw_id']
        ec2_client = session.client('ec2')
        # delete egress vpc routes
        egress_rtb_ids = delete_routes(ec2_client, member_cidr, hub_egress_vpc_id, None)
        # delete internal vpc routes
        intern_rtb_ids = delete_routes(ec2_client, member_cidr, hub_intern_vpc_id, hub_intern_subnet_id)
        # delete route propagation for member vpc in 'Egress-RTB' TGW RTB
        unpropagate_tgw_route(ec2_client, member_account, member_vpc_id, os.environ['EGRESS_TGW_ROUTETABLE'])
        responseData = {
            'member_account': member_account,
            'member_region': member_region,
            'member_vpc_id': member_vpc_id,
            'member_cidr': member_cidr,
            'hub_intern_rtb_ids': intern_rtb_ids,
            'hub_egress_rtb_ids': egress_rtb_ids
        }
        send_response(event, context, 'SUCCESS', responseData)
    except Exception as e:
        LOGGER.error(f'failed in delete_operation(..): {e}')
        LOGGER.error(str(e))
        responseData = {
            'exc_info': str(e)
        }
        send_response(event, context, 'FAILED', responseData)

def lambda_handler(event, context):
    print(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    responseData = {}
    if 'RequestType' in event:
        if event['RequestType'] == 'Create':
            create_operation(event, context)
        elif event['RequestType'] == 'Delete':
            delete_operation(event, context)
        else:
            send_response(event, context, 'SUCCESS', responseData)

#def main():
#    vpc_id = sys.argv[1]
#    subnet_id = sys.argv[2]
#    print('vpc_id = %s' % vpc_id)
#    print('subnet_id = %s' % subnet_id)
#    ec2_client = session.client('ec2')
#    get_rtb(vpc_id, subnet_id)

#if __name__ == '__main__':
#    main()