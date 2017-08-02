# GetSwift Coding Challenge
# Drone Delivery Scenario
# By: Steven Wojsnis

import urllib2
import json
import heapq
import geopy
import time
import pprint
from geopy.distance import vincenty

# Initialize our result lists
deliveredPackages = []
undeliveredPackages = []

# Used for collecting debugging info. Left some debugging info in the program
# as I felt like it would make checking my results a little easier.
# Uncomment lines 234 and 235 to view debugging info
debugInfo = {}

# Obtain JSON data for depot from google maps. Alternative would be to use geopy library
baseAddress = urllib2.urlopen("http://maps.googleapis.com/maps/api/geocode/json?address=303%20Collins%20Street,%20Melbourne,%20VIC%203000")
baseJSON = baseAddress.read()
baseCoords = json.loads(baseJSON)

# Extract the Latitude and Longitude from depot JSON data
baseLat = baseCoords["results"][0]["geometry"]["location"]["lat"]
baseLng = baseCoords["results"][0]["geometry"]["location"]["lng"]
baseLocation = (baseLat, baseLng)

# Retrieve drone JSON data from provided API
drones = urllib2.urlopen("https://codetest.kube.getswift.co/drones")
dronesJSON = drones.read()
dronesData = json.loads(dronesJSON)


# Retrieve package JSON data from provided API
packages = urllib2.urlopen("https://codetest.kube.getswift.co/packages")
packagesJSON = packages.read()
packagesData = json.loads(packagesJSON)

# NOTE: If you want to insert your own JSON strings, rather than obtaining from API,
# comment out lines 33,34,39,40. Then just insert the respective string into each of
# the json.loads() methods.

# For the purpose of testing - easy access to drone/package data to ensure none
# of our drones attempt to deliver packages they won't deliver on time
dronesTestDict = {}
packagesTestDict = {}

# droneHeap is a minheap that sorts droneIds by the amount of time before they return to depot
droneHeap = []

# For each drone...
for drone in dronesData:

    # Extract drone coordinates from drone JSON data
    droneLat = drone["location"]["latitude"]
    droneLng = drone["location"]["longitude"]
    droneLocation = (droneLat, droneLng)

    # Measure distance drone must travel to get to base. Consider whether drone already has package
    if(drone["packages"]):

        # Extract the coordinates of where drone must deliver package before returning to depot
        destLat = drone["packages"][0]["destination"]["latitude"]
        destLng = drone["packages"][0]["destination"]["longitude"]
        destLocation = (destLat, destLng)

        # Uses vincenty method of measuring distance
        distanceToDestinationDrone = vincenty(droneLocation, destLocation).kilometers
        distanceFromDestinationToBase = vincenty(destLocation, baseLocation).kilometers

        distanceFromBase = distanceToDestinationDrone + distanceFromDestinationToBase

        hoursTillBase = distanceFromBase / 50                   # Because the drone moves at 50km/h
        secondsTillBase = hoursTillBase * 60 * 60               # To convert hours to seconds

        dronesTestDict[drone["droneId"]] = secondsTillBase      # For testing later

        heapq.heappush(droneHeap, (secondsTillBase, drone["droneId"]))

    else:
         # Uses vincenty method of measuring distance
         distanceFromBase = vincenty(droneLocation, baseLocation).kilometers

         hoursTillBase = distanceFromBase / 50                   # Because the drone moves at 50km/h
         secondsTillBase = hoursTillBase * 60 * 60               # To convert hours to seconds

         dronesTestDict[drone["droneId"]] = secondsTillBase      # For testing later

         heapq.heappush(droneHeap, (secondsTillBase, drone["droneId"]))


mostUrgentPackages = []               # Heap to sort packages by how soon they'll expire
shortestDeliveryPackages = []         # Heap to sort packages by how long it'll take them to be delivered
processed = set();                    # Since we have two heaps, this allows us to keep track of packages that have been processed

# Repeat the process above for packages
for package in packagesData:

    # Get package destination / distance to that destination
    packageDestLat = package["destination"]["latitude"]
    packageDestLng = package["destination"]["longitude"]
    packageDestLocation = (packageDestLat, packageDestLng)
    distanceToDestinationPackage =  vincenty(baseLocation, packageDestLocation).kilometers

    # Determine seconds it would take to deliver package
    hoursToDeliver = distanceToDestinationPackage / 50
    secondsToDeliver = hoursToDeliver * 60 * 60

    # ExpiryTime represents how long a package can wait for a drone to arrive
    # If a drone isn't within ExpiryTime seconds of the depot, the package will expire
    expiryTime = (package["deadline"] - time.time() - secondsToDeliver)

    # If it's impossible for the package to be delivered (it's too far away, will
    # expire even if its delivery begins immediately)
    if(expiryTime < 0):
        undeliveredPackages.append(package["packageId"]);
    else:
        packagesTestDict[package["packageId"]] = expiryTime #For testing

        # Add package to both heaps with the corresponding data. Note secondsToDeliver
        # is multiplied by two, because the drone must deliver and return (two-way travel)
        heapq.heappush(shortestDeliveryPackages, (secondsToDeliver*2, package["packageId"], expiryTime))
        heapq.heappush(mostUrgentPackages, (expiryTime, package["packageId"]))

debugInfo["Packages that expired before first drone arrived "] = len(undeliveredPackages) # DEBUGGING PURPOSES
debugInfo["Total number of packages "] = len(mostUrgentPackages) + len(undeliveredPackages) # DEBUGGING PURPOSES

debugInfo["Number of drones "] = len(droneHeap) # DEBUGGING PURPOSES

# Loop while there are still drones and packages
while(droneHeap and (mostUrgentPackages or shortestDeliveryPackages)):

    # Obtain the drone that is closest to returning to depot
    currDrone = heapq.heappop(droneHeap)
    currDroneTime = currDrone[0]
    currDroneId = currDrone[1]

    # If there's another drone (second closest to returning), obtain it
    if(droneHeap):
        nextDrone = droneHeap[0]

    # These two while blocks essentially check if the top of each package stack cannot
    # be delivered on time with the current drone, or has already been processed.
    # It continues to pop packages (discard) off the stack while this is true, as
    # we don't want to attempt deliver those packages

    while(mostUrgentPackages and ((mostUrgentPackages[0][1] in processed)
    or (mostUrgentPackages[0][0] - currDroneTime < 0))):
        package = heapq.heappop(mostUrgentPackages)
        if(package[1] not in processed):
            undeliveredPackages.append(package[1])
            processed.add(package[1])

    while(shortestDeliveryPackages and ((shortestDeliveryPackages[0][1] in processed)
    or (shortestDeliveryPackages[0][0] - currDroneTime < 0))):

        package = heapq.heappop(shortestDeliveryPackages)
        if(package[1] not in processed):
            undeliveredPackages.append(package[1])
            processed.add(package[1])


    # If there are still packages waiting to be delivered
    if(mostUrgentPackages and shortestDeliveryPackages):
        urgentPack = mostUrgentPackages[0]
        shortPack = shortestDeliveryPackages[0]

        # If the package with the shortest delivery time can be delivered, and have
        # the drone return in time to still deliver the most urgent package, deliver
        # the one with the shorter delivery time.
        if((shortPack[0] + currDroneTime) <= urgentPack[0]):
            assignedPackageId = heapq.heappop(shortestDeliveryPackages)[1]
            assignment = {'droneId': currDroneId, 'packageId': assignedPackageId}
            processed.add(assignedPackageId)
            deliveredPackages.append(assignment)

        else:
            # Otherwise, if taking the most urgent package will cause the package with
            # the short delivery to expire (also checks to see if the next availble droneId
            # will make it in time to deliver it), then take the short-delivery package instead
            if(((urgentPack[0] + currDroneTime) > shortPack[2]) and (shortPack[2] > nextDrone[0])):
                 assignedPackageId = heapq.heappop(shortestDeliveryPackages)[1]
                 assignment = {'droneId': currDroneId, 'packageId': assignedPackageId}
                 processed.add(assignedPackageId)
                 deliveredPackages.append(assignment)

            # Otherwise, just deliver the most urgent package
            else:
                assignedPackageId = heapq.heappop(mostUrgentPackages)[1]
                assignment = {'droneId': currDroneId, 'packageId': assignedPackageId}
                processed.add(assignedPackageId)
                deliveredPackages.append(assignment)

# These two while blocks ensure that, if we have less drones than packages, the
# leftover packages are added to the undeliveredPackages list

while(mostUrgentPackages):
    package = heapq.heappop(mostUrgentPackages)
    if(package[1] not in processed):
        undeliveredPackages.append(package[1])
        processed.add(package[1])

while(shortestDeliveryPackages):
    package = heapq.heappop(shortestDeliveryPackages)
    if(package[1] not in processed):
        undeliveredPackages.append(package[1])
        processed.add(package[1])


print"Assigned: ",deliveredPackages
print"Unassigned: ", undeliveredPackages

debugInfo["Number of delivered Packages"] = len(deliveredPackages) # DEBUGGING PURPOSES
debugInfo["Number of undelivered Packages"] = len(undeliveredPackages) # DEBUGGING PURPOSES

# FOR DEBUGGING PURPOSES
def validateDroneDelivery():
    for a in deliveredPackages:
        droneTime = dronesTestDict[a["droneId"]]
        packageExpire = packagesTestDict[a["packageId"]]

        if(droneTime > packageExpire):
            debugInfo["Any drones attempt to deliver package after package deadline?"] =  True
            return;

    debugInfo["Any drones attempt to deliver package after package deadline?"] =  False


# FOR DEBUGGING PURPOSES - uncomment for specifications about the assignment process
# validateDroneDelivery();
# pprint.pprint(debugInfo)
