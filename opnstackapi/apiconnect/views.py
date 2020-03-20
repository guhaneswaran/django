import json
import logging

import munch
import openstack
from django.shortcuts import render

# Create your views here.

logger = logging.getLogger(__name__)

"""
Home  - Connects to the page for user to provide inputs
"""


def home(request):
    return render(request, 'home.html')


""" privatenetwork  will be called when the user wishes to attach VM to a private network
 conn - Connection established with Openstack
 nw_name - The name of the private network 
 sb_name - Name of the subnet to be associated with the private network
 rtr_name - Name of the router which connects to the external network at the other end
 cidr - CIDR of the subnet
 
 Returns the Private Network Name if successful or None in case of failure
"""


def privatenetwork(conn, nw_name, sb_name, rtr_name, cidr):
    try:

        if conn.get_router(name_or_id=rtr_name) is None and conn.get_subnet(
                name_or_id=sb_name) is None and conn.get_network(name_or_id=nw_name) is None:

            # Create router
            router = conn.create_router(name=rtr_name,
                                        ext_gateway_net_id='3a89c8a8-1aa0-4ea8-8755-14def2df5dbb')  # net_id is the external_network ID

            if json.loads(munch.toJSON(router))['id']:
                # Create Private Network
                private_network = conn.create_network(name=nw_name)
                if json.loads(munch.toJSON(private_network))['id']:
                    # Create Subnet
                    private_subnet = conn.create_subnet(subnet_name=sb_name, network_name_or_id=nw_name,
                                                        cidr=cidr)
                    if json.loads(munch.toJSON(private_subnet))['id']:
                        # Connect router with the private network
                        add_rtr = conn.add_router_interface(router=router,
                                                            subnet_id=json.loads(munch.toJSON(private_subnet))['id'])
                        print(add_rtr)
                        print(private_network)
                        print(private_subnet)
                        print(router)

        else:
            logger.debug('Duplicate entries present in network details')
            return None

    except Exception as e:
        print('Private N/W creation failed')
        print(e)
        logger.debug(e)
        return None

    return nw_name


"""
createvm - Creates VM based on user input from 'Home'
- Establishes a connection with Openstack environment
- Gives error if the provided input clashes with the existing records
- If user enters Network details, then a private network is created by calling privatenetwork function
    else, external_network is chosen by default
    
 returns result html page which shows the VM creation status
"""


def createvm(request):
    vm_id = None

    try:
        # Establish a connection
        conn = openstack.connection.Connection(
            region_name='RegionOne',
            auth=dict(
                auth_url='http://192.168.43.125:5000/v3',
                username='admin',
                password='admin123',
                project_id='e0875629f3834e42a941aad3b8823cfc',
                user_domain_id='default'),
            compute_api_version='2',
            identity_interface='internal')

        try:
            nw_name = request.POST['nwname']
            sb_name = request.POST['sbname']
            rtr_name = request.POST['rtr']
            cidr = request.POST['cidr']

            # Check user network options
            if nw_name or sb_name or rtr_name or cidr:
                instance_network = privatenetwork(conn, nw_name, sb_name, rtr_name, cidr)
            else:
                instance_network = 'external_network'

            instance_name = request.POST['name']
            instance_flavor = request.POST['flav']
            instance_image = request.POST['img']

            print(instance_name)

            # print(conn.get_server(name_or_id=instance_name))

            # Perform validation of input.
            if instance_network and conn.get_network(name_or_id=instance_network):
                if conn.get_server(name_or_id=instance_name) is None:
                    if conn.get_flavor(name_or_id=instance_flavor):
                        if conn.get_image(name_or_id=instance_image):
                            try:
                                # Create Instance
                                server = conn.create_server(instance_name, image=instance_image, flavor=instance_flavor,
                                                            auto_ip=True, ips=None,
                                                            ip_pool=None,
                                                            root_volume=None,
                                                            terminate_volume=False, wait=False, timeout=180,
                                                            reuse_ips=True,
                                                            network=instance_network,
                                                            boot_from_volume=False, volume_size='50', boot_volume=None,
                                                            volumes=None,
                                                            nat_destination=None,
                                                            group=None)

                                print(json.loads(munch.toJSON(server))['id'])

                                vm_id = json.loads(munch.toJSON(server))['id']

                                res = ' VM Creation Successful'

                                logger.debug('Server Details :', server)

                            except Exception as e:
                                # VM Creation
                                # res = 'Failed'
                                logger.debug(e)
                                res = 'VM Creation Failed'

                        else:
                            print("image not present")
                            res = 'image not present'

                    else:
                        print("flavour not present")
                        res = 'flavour not present'
                else:
                    print("VM already present")
                    res = 'VM name already exists'
            else:
                print("nw not present")
                res = 'external nw not present/private nw creation failed'
        except Exception as e:
            res = 'Unable to get Flavour/Image/Network Details'
            logger.debug(e)
    except Exception as e:
        logger.debug(e)
        res = 'Connection to Openstack server unsuccessful'

    if not (res.find('Successful')):
        res = 'VM Creation Failed ::' + res

    return render(request, 'result.html', {'result': res, 'id': vm_id})
