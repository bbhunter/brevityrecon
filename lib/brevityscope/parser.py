import tldextract
import pandas as pd

def generateInitialDomains(programName, refinedBucketPath, listscopein, programInputBucketPath):
    dfInputScope = pd.DataFrame(listscopein)
    dfInputScope.columns=['domain']
    # Generate a list of all of the unique domains while parsing potentially missing child domains
    allDomains = processBulkDomains(dfInputScope)
    # Store the unique list of domains into S3 - Creates file - programName-domains.csv
    storeStatus = storeAllDomains(programName, refinedBucketPath, allDomains, programInputBucketPath)
    scopeStatus = storeScopeDomains(programName, refinedBucketPath, allDomains, programInputBucketPath)
    return storeStatus

def cleanupScopeFiles(dfIn):
    dfIn.columns=['ScopeIn']
    dfIn = dfIn[~dfIn.ScopeIn.str.contains('[ ]')]
    dfIn.ScopeIn = dfIn.ScopeIn.str.replace('https://','')
    dfIn.ScopeIn = dfIn.ScopeIn.str.replace('http://','')
    dfIn.ScopeIn = dfIn.ScopeIn.str.replace('\*.','')
    return dfIn

def parseRootDomains(refinedBucketPath, programName):
    storePathInitial = refinedBucketPath + programName + '/' + programName + '-domains.csv'   
    dfAllDomains = pd.read_csv(storePathInitial)
    allDomains = dfAllDomains['domain'].unique().tolist()
    domainEdges = []
    for val in allDomains:
        domainEdges.append(processDomainRoots(val))
    # Convert to set to remove duplicates from list
    setUniqueRoots = set(domainEdges)
    # Copy set into new list
    lstUniqueRoots = (list(setUniqueRoots)) 
    dfRoots = pd.DataFrame(lstUniqueRoots)
    dfRoots.columns = ['domain']
    storePathRoots = refinedBucketPath + programName + '/' + programName + '-domains-roots.csv'
    try:
        dfInitialRoots = pd.read_csv(storePathRoots)
    except:
        lstEmpty = []
        dfInitialRoots = pd.DataFrame(lstEmpty,columns=['domain'])
    dfNewRoots = dfInitialRoots.merge(dfRoots, how ='outer',indicator=True).loc[lambda x : x['_merge']=='right_only']
    dfNewRoots = pd.DataFrame(dfNewRoots['domain'])
    if (len(dfNewRoots) > 0):
        dfRoots = dfNewRoots.append(dfInitialRoots)
        dfRoots = dfRoots.drop_duplicates()
        dfRoots.to_csv(storePathRoots, index=False)
    return dfNewRoots

# Return only the root domains
def processDomainRoots(domainName):
    ext = tldextract.extract(domainName)
    if (ext.suffix is not ''):
        rootDomain = ext.domain + '.' + ext.suffix
    else:
        rootDomain = ext.domain
        subs = ext.subdomain.split('.')
        subLength = len(subs) - 1
        rootDomain = subs[subLength] + '.' + rootDomain
    return rootDomain
    
# Generate a list of all of the unique domains while parsing potentially missing child domains
def processBulkDomains(dfAmass):
    listDomains = []
    try:
        listDomains = dfAmass['subdomain'].unique().tolist()
    except:
        print('No subdomain column')
    try:
        listDomains += dfAmass['domain'].unique().tolist()
    except:
        print('No domain column')
    tempDomains = []
    for val in listDomains: 
        tempDomains = processSingleDomain(val)
        listDomains = listDomains + tempDomains
    setDomains = set(listDomains)
    return setDomains


# This code is so confusing, but it does somehow work. I will re-visit this to provide better documentation and cleanup around the intent of the various file inputs and outputs.
# If there are any logic flaws in the code, they are probably somewhere in here.
def storeAllDomains(programName, refinedBucketPath, lstDomains, programInputBucketPath):
    dfDomains = pd.DataFrame(lstDomains)
    print('Length of scope domains: ' + str(len(dfDomains)))
    storePathUnique = programInputBucketPath + programName + '/' + programName + '-domains-all.csv'
    storePathNew = programInputBucketPath + programName + '/' + programName + '-domains-new.csv'
    dfDomains.rename({0: 'domain'}, axis=1, inplace=True)
    try:
        storePath = refinedBucketPath + programName + '/' + programName + '-domains.csv'
        dfExistingDomains = pd.read_csv(storePath)
    except:
        lstEmpty = []
        dfExistingDomains = pd.DataFrame(lstEmpty,columns=['domain'])
    print('Initial length of unique subdomains: ' + str(len(dfExistingDomains)))
    dfNewDomains = dfExistingDomains.merge(dfDomains, how ='outer',indicator=True).loc[lambda x : x['_merge']=='right_only']
    dfNewDomains = pd.DataFrame(dfNewDomains['domain'])
    print('Length of unique subdomains after new domains added: ' + str(len(dfNewDomains)))
    if (len(dfNewDomains) > 0):
        dfNewDomains.to_csv(storePathNew, header=False, index=False, sep='\n')
        dfDomains = dfDomains.append(dfExistingDomains)
        dfDomains = dfDomains.drop_duplicates()
        dfDomains.to_csv(storePath, index=False)
        dfDomains.to_csv(storePathUnique, header=False, index=False, sep='\n')
        print('Updated length of unique subdomains: ' + str(len(dfDomains)))
        # Every time the domain all list is updated, also update the roots list
        dfDomainRoots = parseRootDomains(refinedBucketPath, programName)
    return 'Success'
    
def storeScopeDomains(programName, refinedBucketPath, lstDomains, programInputBucketPath):
    dfDomains = pd.DataFrame(lstDomains)
    print('Length of scope domains: ' + str(len(dfDomains)))
    storePathScope = refinedBucketPath + programName + '/' + programName + '-domains-scope.csv'
    dfDomains.rename({0: 'domain'}, axis=1, inplace=True)
    print('Length of scope domains: ' + str(len(dfDomains)))
    try:
        dfExistingDomains = pd.read_csv(storePathScope, header=None)
        dfExistingDomains.rename({0: 'domain'}, axis=1, inplace=True)
    except:
        lstEmpty = []
        dfExistingDomains = pd.DataFrame(lstEmpty,columns=['domain'])
    dfNewDomains = dfExistingDomains.merge(dfDomains, how ='outer',indicator=True).loc[lambda x : x['_merge']=='right_only']
    dfNewDomains = pd.DataFrame(dfNewDomains['domain'])
    if (len(dfNewDomains) > 0):
        dfDomains = dfDomains.append(dfExistingDomains)
        dfDomains = dfDomains.drop_duplicates()
        dfDomains.to_csv(storePathScope, header=False, index=False, sep='\n')
        print('Updated length of unique subdomains: ' + str(len(dfDomains)))
    return 'Success'
    
def processSingleDomain(domainName):
    domainList = []
    ext = tldextract.extract(domainName)
    if (ext.suffix is not ''):
        rootDomain = ext.domain + '.' + ext.suffix
        domainList.append(rootDomain)
        if (ext.subdomain is not ''):
            subDomain = ext.subdomain
            subs = subDomain.split('.')
            subLength = len(subs) - 1
            while subLength >= 0:
                rootDomain = subs[subLength] + '.' + rootDomain
                domainList.append(rootDomain)
                subLength = subLength - 1
    else:
        rootDomain = ext.domain
        domainList.append(rootDomain)
        subDomain = ext.subdomain
        subs = subDomain.split('.')
        subLength = len(subs) - 1
        while subLength >= 0:
            rootDomain = subs[subLength] + '.' + rootDomain
            domainList.append(rootDomain)
            subLength = subLength - 1
    return domainList