#!/usr/bin/python

import os, shutil, subprocess
from ctypes import *
from ctypes.util import find_library

libDS = CDLL(find_library('DirectoryService'))

class tDataBuffer(Structure):
    _fields_ = [
        ('fBufferSize', c_uint32),
        ('fBufferLength', c_uint32),
        ('fBufferData', c_char * 1)]


class tDataNode(tDataBuffer):
    pass


class tDataList(Structure):
    _fields_ = [
        ('fDataNodeCount', c_uint32),
        ('fDataListHead', POINTER(tDataNode))]


class tAccessControlEntry(Structure):
    _fields_ = [
        ('fGuestAccessFlags', c_uint32),
        ('fDirMemberFlags', c_uint32),
        ('fDirNodeMemberFlags', c_uint32),
        ('fOwnerFlags', c_uint32),
        ('fAdministratorFlags', c_uint32)]


class tRecordEntry(Structure):
    _fields_ = [
        ('fReserved1', c_uint32),
        ('fReserved2', tAccessControlEntry),
        ('fRecordAttributeCount', c_uint32),
        ('fRecordNameAndType', tDataNode)]


class tAttributeEntry(Structure):
    _fields_ = [
        ('fReserved1', c_uint32),
        ('fReserved2', tAccessControlEntry),
        ('fAttributeValueCount', c_uint32),
        ('fAttributeDataSize', c_uint32),
        ('fAttributeValueMaxSize', c_uint32),
        ('fAttributeSignature', tDataNode)]


class tAttributeValueEntry(Structure):
    _fields_ = [
        ('fAttributeValueID', c_uint32),
        ('fAttributeValueData', tDataNode)]


def get_DataNode_buffer(dn_obj):
    # Doing pointer math here as the tDataNode struct only has a single char value (to python)
    recast_obj = cast(addressof(dn_obj), POINTER(tDataNode))
    return cast(addressof(recast_obj.contents) + tDataNode.fBufferData.offset,
                POINTER(c_char * (recast_obj.contents.fBufferLength))).contents[:]


dsDataBufferAllocate = libDS.dsDataBufferAllocate
dsDataBufferAllocate.restype = POINTER(tDataBuffer)
dsBuildListFromStrings = libDS.dsBuildListFromStrings
dsBuildListFromStrings.restype = POINTER(tDataList)

# Use when searching for local and network
eDSAuthenticationSearchNodeName = 0x2201
# Use when searching for network accounts only.
eDSContactsSearchNodeName = 0x2204
# Use when searching for local
eDSLocalNodeNames = 0x2200
# Match name exactly
eDSiExact = 0x2101


def ds_user_exists(username, search_base):
    dirRef = c_uint32(0)
    # Connect to DS
    status = libDS.dsOpenDirService(byref(dirRef))
    if status != 0:
        return -1

    dataBuff = dsDataBufferAllocate(dirRef, 2 * 1024);
    numResults = c_uint32(0)
    context = c_uint32(0)
    # Find the authentication search node
    status = libDS.dsFindDirNodes(dirRef, dataBuff, None, search_base, byref(numResults), byref(context))
    if (status != 0) or (numResults.value != 1L):
        return -2

    nodePath = POINTER(tDataList)()
    # Get the authentication search node name
    status = libDS.dsGetDirNodeName(dirRef, dataBuff, 1, byref(nodePath))
    if status != 0:
        return -3

    # Clean up old buffer, make a new one
    _ = libDS.dsDataBufferDeAllocate(dirRef, dataBuff)

    nodeRef = c_uint32(0)
    # Open the search node
    status = libDS.dsOpenDirNode(dirRef, nodePath, byref(nodeRef))
    if status != 0:
        return -4

    # Build search terms
    recName = dsBuildListFromStrings(dirRef, username, None)
    recType = dsBuildListFromStrings(dirRef, "dsRecTypeStandard:Users", None)
    attrTypes = dsBuildListFromStrings(dirRef, "dsAttrTypeNative:name", None)

    numResults = c_uint32(0)
    context = c_uint32(0)
    dataBuff = None
    dataBuff = dsDataBufferAllocate(dirRef, 8 * 1024)
    # Perform user object lookup
    status = libDS.dsGetRecordList(nodeRef, dataBuff, recName, eDSiExact, recType, attrTypes, 0, byref(numResults),
                                   byref(context))
    if status != 0:
        return -5

    # Cleanup
    status = libDS.dsDataListDeallocate(dirRef, recName)
    status = libDS.dsDataListDeallocate(dirRef, recType)
    status = libDS.dsDataListDeallocate(dirRef, attrTypes)
    _ = libDS.dsDataBufferDeAllocate(dirRef, dataBuff)
    libDS.dsCloseDirNode(nodeRef)
    libDS.dsCloseDirService(dirRef)
    # 1 or more = account exists
    return int(numResults.value)


class Nomadize(object):
    def __init__(self, (local_user_path, local_user_name), (ad_user_path, ad_user_name)):

        self.local_user_path = local_user_path
        self.ad_user_path = ad_user_path
        self.local_user_name = local_user_name
        self.ad_user_name = ad_user_name

    def create_mobile(self):

        print "Deleting old local account"

        shutil.move(self.local_user_path, "%s.Nomadize" % self.local_user_path)

        try:
            subprocess.check_call(['/usr/bin/dscl', '.', '-delete', '/Users/' + self.local_user_name])
        except subprocess.CalledProcessError, err:
            print "[* Error] [%s] deleting [%s]" % (err, self.local_user_name)

        print "Creating new AD Mobile account"

        try:
            subprocess.check_call(
                ['/System/Library/CoreServices/ManagedClient.app/Contents/Resources/createmobileaccount', '-n',
                 self.ad_user_name])
        except subprocess.CalledProcessError, err:
            print "%s creating %s" % (err, self.ad_user_name)

    def set_own(self):

        print "Setting ownership"

        try:
            group_id = subprocess.check_output(['/usr/bin/id', '-g', self.ad_user_name]).replace("\n","")
        except subprocess.CalledProcessError, err:
            print "%s finding Group ID for: %s" % (err, self.ad_user_name)

        try:
            subprocess.check_call(['/usr/sbin/chown', '-R', "%s:%s" % (self.ad_user_name, group_id), self.ad_user_path])
        except subprocess.CalledProcessError, err:
            print "%s setting %s" % (err, self.ad_user_name)

    def move_data(self):
        shutil.move(self.ad_user_path, "%s.Nomadize_empty" % self.ad_user_path)
        shutil.move(self.local_user_path + ".Nomadize", self.ad_user_path)


class UserInput(object):
    def __init__(self):
        print ""

    def choose_local(self):
        users = os.listdir("/Users/")
        for e in users:
            print "Choose [%d] for [%s]" % ((users.index(e) + 1), e)

        while True:
            user_input = raw_input(
                "\nPlease choose the source account. If the account is not stored under /Users/ please move it to that path: ")
            try:
                int(user_input)
                if int(user_input) in range(1, users.index(users[-1]) + 2):
                    break
                else:
                    print "\n[+] Please choose a valid entry"
            except ValueError:
                print "\n[+] Please choose a valid entry"

        local_user = ("/Users/" + users[(int(user_input) - 1)], users[(int(user_input) - 1 )])
        return local_user

    def choose_ad(self):
        while True:
            user = raw_input("\nPlease type in the new AD account: ")
            if (ds_user_exists(user, eDSContactsSearchNodeName) > 0):
                    break
        ad_user = ("/Users/" + user, user)
        return ad_user



userInput = UserInput()
nomadize = Nomadize(userInput.choose_local(), userInput.choose_ad())
nomadize.create_mobile()
nomadize.move_data()
nomadize.set_own()
