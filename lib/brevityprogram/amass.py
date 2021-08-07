import boto3
import io, json
import pandas as pd
import brevitycore.core
import brevityprogram.dynamodb

# Initial function for program specific amass configuration
def prepareAmass(programName, inputBucketName, inputBucketPath):
    # Generate and upload amass scope files to S3
    # This returns all of the data for the program retrieved from DynamoDB
    scopes = brevityprogram.dynamodb.query_program(programName)
    # Create the Amass config file and load all of the API keys dynamically from AWS Secrets Manager
    configStatus = generateAmassConfig(inputBucketName)
    # This will create the scope files from the DynamoDB table and load them into S3
    scopeStatus = generateScopeFiles(inputBucketPath, programName, scopes)
    # Generate amass command specific to the program details
    scriptStatus = generateScriptAmass(programName, inputBucketName)
    return scriptStatus
    
# Generate consumable scope files for amass
# TODO: This should be cleaned and updated to use standardized scope functions
def generateScopeFiles(bucketPath, programName, scopes):
    try:
        dfIn = pd.DataFrame(dynjson.loads(scopes['ScopeInGeneral']))
        dfIn = cleanupScopeFiles(dfIn)
        
        # Export the dataframe to S3 as an input scope 
        fileName = programName + '-in.txt'
        filePath = bucketPath + 'scope/' + programName + '/' + fileName
        dfIn.to_csv(filePath, index=False, header=False, encoding='utf-8', sep='\n')

        # Cleanup the JSON return value
        dfOut = pd.DataFrame(dynjson.loads(scopes['ScopeOutGeneral']))
        dfOut.columns=['ScopeOut']
        
        # TODO: This section likely needs better tuned
        # The scope field stores everything so it needs to be cleaned up for automation
        # Remove any seeds with a space as this indicates that it is not a domain
        # Remove the beginning of specific urls as we still want to include subs for recon
        dfOut = dfOut[~dfOut.ScopeOut.str.contains('[ ]')]
        dfOut.ScopeOut = dfOut.ScopeOut.str.replace('https://','')
        dfOut.ScopeOut = dfOut.ScopeOut.str.replace('http://','')
        dfOut.ScopeOut = dfOut.ScopeOut.str.replace('\*.','')

        # Export the dataframe to S3 as an output scope 
        fileName = programName + '-out.txt'
        filePath = bucketPath + 'scope/' + programName + '/' + fileName
        dfOut.to_csv(filePath, index=False, header=False, encoding='utf-8', sep='\n')
        return "Scope generation succeeded."
    except:
        return "Scope generation failed."
        
def generateScriptAmass(programName, inputBucketName):
    fileBuffer = io.StringIO()
    fileContents = f"""#!/bin/bash

# Run custom amass script
export HOME=/root
cd $HOME/security/tools/amass
amass enum -config config.ini -blf {programName}-out.txt -df {programName}-in.txt -json {programName}-amass-subs.json
mkdir $HOME/security/raw/{programName}
sleep 5
mv *.json $HOME/security/refined/{programName}/
sleep 10
mv db/amass.txt $HOME/security/refined/{programName}/{programName}-amass-subs.txt
sleep 10
sh $HOME/security/config/sync-{programName}.sh
sleep 10
shutdown now"""
    fileBuffer.write(fileContents)
    objectBuffer = io.BytesIO(fileBuffer.getvalue().encode())
    # Upload file to S3
    object_name = 'amass-' + programName + '.sh'
    object_path = 'run/' + programName + '/' + object_name
    status = brevitycore.core.upload_object(objectBuffer,inputBucketName,object_path)
    fileBuffer.close()
    objectBuffer.close()
    return status
    
def generateAmassConfig(inputBucketName):
    
    secret_name = "brevity-recon-apis"
    region_name = "us-east-1"
    secretRetrieved = brevitycore.core.get_secret(secretName,regionName)
    secretjson = json.loads(secretRetrieved)
    alienvault = secretjson['alienvault']
    binaryedge = secretjson['binaryedge']
    censysapikey = secretjson['censysapikey']
    censyssecret = secretjson['censyssecret']
    cloudflare = secretjson['cloudflare']
    github = secretjson['github']
    networksdb = secretjson['networksdb']
    passivetotalusername = secretjson['passivetotalusername']
    passivetotalapikey = secretjson['passivetotalapikey']
    securitytrails = secretjson['securitytrails']
    shodan = secretjson['shodan']
    spyse = secretjson['spyse']
    urlscan = secretjson['urlscan']
    virustotal = secretjson['virustotal']
    whoisxml = secretjson['whoisxml']
    
    fileBuffer = io.StringIO()
    fileContents = f"""# Copyright 2017-2020 Jeff Foley. All rights reserved.
# Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

# Should results only be collected passively and without DNS resolution? Not recommended.
#mode = passive
# Would you like to use active techniques that communicate directly with the discovered assets, 
# such as pulling TLS certificates from discovered IP addresses and attempting DNS zone transfers?
#mode = active

# The directory that stores the Cayley graph database and other output files
# The default for Linux systems is: $HOME/.config/amass
output_directory = db

# Another location (directory) where the user can provide ADS scripts to the engine.
#scripts_directory = 

# The maximum number of DNS queries that can be performed concurrently during the enumeration.
#maximum_dns_queries = 20000

# DNS resolvers used globally by the amass package.
#[resolvers]
#monitor_resolver_rate = true
#resolver = 1.1.1.1 ; Cloudflare
#resolver = 8.8.8.8 ; Google
#resolver = 64.6.64.6 ; Verisign
#resolver = 74.82.42.42 ; Hurricane Electric
#resolver = 1.0.0.1 ; Cloudflare Secondary
#resolver = 8.8.4.4 ; Google Secondary
#resolver = 64.6.65.6 ; Verisign Secondary
#resolver = 77.88.8.1 ; Yandex.DNS Secondary

[scope]
# The network infrastructure settings expand scope, not restrict the scope.
# Single IP address or range (e.g. a.b.c.10-245)
#address = 192.168.1.1
#cidr = 192.168.1.0/24
#asn = 26808
#port = 80
port = 443
#port = 8080

# Root domain names used in the enumeration. The findings are limited by the root domain names provided.
#[scope.domains]
#domain = owasp.org
#domain = appsecusa.org
#domain = appsec.eu
#domain = appsec-labs.com

# Are there any subdomains that are out of scope?
#[scope.blacklisted]
#subdomain = education.appsec-labs.com
#subdomain = 2012.appsecusa.org

# The graph database discovered DNS names, associated network infrastructure, results from data sources, etc.
# This information is then used in future enumerations and analysis of the discoveries.
#[graphdbs]
#local_database = false; Set this to false to disable use of the local database.
#[graphdbs.neo4j]
#url = wss://0000000.databases.neo4j.io
#primary = true;
#url = neo4j://000000.databases.neo4j.io:7687
#username = neo4j
#password =
#dbname = neo4j
# postgres://[username:password@]host[:port]/database-name?sslmode=disable of the PostgreSQL 
# database and credentials. Sslmode is optional, and can be disable, require, verify-ca, or verify-full.
#[graphdbs.postgres]
#primary = false ; Specify which graph database is the primary db, or the local database will be selected.
#url = "postgres://[username:password@]host[:port]/database-name?sslmode=disable"
#options="connect_timeout=10"

# MqSQL database and credentials URL format:
# [username:password@]tcp(host[:3306])/database-name?timeout=10s
#[graphdbs.mysql]
#url = [username:password@]tcp(host[:3306])/database-name?timeout=10s

# Settings related to DNS name brute forcing.
#[bruteforce]
#enabled = true
#recursive = true
# Number of discoveries made in a subdomain before performing recursive brute forcing: Default is 1.
#minimum_for_recursive = 1
#wordlist_file = /usr/share/wordlists/all.txt
#wordlist_file = /usr/share/wordlists/all.txt # multiple lists can be used

# Would you like to permute resolved names?
#[alterations]
#enabled = true
# edit_distance specifies the number of times a primitive edit operation will be
# performed on a name sample during fuzzy label searching.
#edit_distance = 1 ; Setting this to zero will disable this expensive feature.
#flip_words = true   # test-dev.owasp.org -> test-prod.owasp.org
#flip_numbers = true # test1.owasp.org -> test2.owasp.org
#add_words = true    # test.owasp.org -> test-dev.owasp.org
#add_numbers = true  # test.owasp.org -> test1.owasp.org
# Multiple lists can be used.
#wordlist_file = /usr/share/wordlists/all.txt
#wordlist_file = /usr/share/wordlists/all.txt

[data_sources]
# When set, this time-to-live is the minimum value applied to all data source caching.
minimum_ttl = 1440 ; One day

# Are there any data sources that should be disabled?
#[data_sources.disabled]
#data_source = Ask
#data_source = Exalead
#data_source = IPv4Info

# Provide data source configuration information.
# See the following format:
#[data_sources.SOURCENAME] ; The SOURCENAME must match the name in the data source implementation.
#ttl = 4320 ; Time-to-live value sets the number of minutes that the responses are cached.
# Unique identifier for this set of SOURCENAME credentials.
# Multiple sets of credentials can be provided and will be randomly selected.
#[data_sources.SOURCENAME.CredentialSetID]
#apikey = ; Each data source uses potentially different keys for authentication.
#secret = ; See the examples below for each data source.
#username =
#password =

#https://otx.alienvault.com (Free)
[data_sources.AlienVault]
[data_sources.AlienVault.Credentials]
apikey = {alienvault}

#https://app.binaryedge.com (Free)
[data_sources.BinaryEdge]
ttl = 10080
[data_sources.BinaryEdge.Credentials]
apikey = {binaryedge}

#https://c99.nl (Paid) - $25 year - 100,000 requests
#[data_sources.C99]
#ttl = 4320
#[data_sources.C99.account1]
#apikey=
#[data_sources.C99.account2]
#apikey=

#https://censys.io (Free)
[data_sources.Censys]
ttl = 10080
[data_sources.Censys.Credentials]
apikey = {censysapikey}
secret = {censyssecret}

#https://chaos.projectdiscovery.io (Free-InviteOnly)
#[data_sources.Chaos]
#ttl = 4320
#[data_sources.Chaos.Credentials]
#apikey=

#https://cloudflare.com (Free)
[data_sources.Cloudflare]
[data_sources.Cloudflare.Credentials]
apikey = {cloudflare}

#Closed Source Invite Only
#[data_sources.CIRCL]
#[data_sources.CIRCL.Credentials]
#username =
#password =

#https://dnsdb.info (Paid)
#[data_sources.DNSDB]
#ttl = 4320
#[data_sources.DNSDB.Credentials]
#apikey =

#https://developer.facebook.com (Free)
# Look here for how to obtain the Facebook credentials:
# https://goldplugins.com/documentation/wp-social-pro-documentation/how-to-get-an-app-id-and-secret-key-from-facebook/
#[data_sources.FacebookCT]
#ttl = 4320
#[data_sources.FacebookCT.app1]
#apikey=
#secret=
#[data_sources.FacebookCT.app2]
#apikey=
#secret=

#https://github.com (Free)
[data_sources.GitHub]
ttl = 4320
[data_sources.GitHub.accountname]
apikey = {github}

#https://networksdb.io (Free)
[data_sources.NetworksDB]
[data_sources.NetworksDB.Credentials]
apikey = {networksdb}

#https://passivetotal.com (Free)
[data_sources.PassiveTotal]
ttl = 10080
[data_sources.PassiveTotal.Credentials]
username = {passivetotalusername}
apikey = {passivetotalapikey}

#https://recon.dev (Free)
#[data_sources.ReconDev]
#[data_sources.ReconDev.free]
#apikey = 
#[data_sources.ReconDev.paid]
#apikey = 

#https://securitytrails.com (Free)
[data_sources.SecurityTrails]
ttl = 1440
[data_sources.SecurityTrails.Credentials]
apikey = {securitytrails}

#https://shodan.io (Free)
[data_sources.Shodan]
ttl = 10080
[data_sources.Shodan.Credentials]
apikey = {shodan}

#https://spyse.com (Paid/Free-trial)
#[data_sources.Spyse]
#ttl = 4320
#[data_sources.Spyse.Credentials]
#apikey = {spyse}

#https://developer.twitter.com (Free)
# Provide your Twitter App Consumer API key and Consumer API secrety key
#[data_sources.Twitter]
#[data_sources.Twitter.account1]
#apikey =
#secret =
#[data_sources.Twitter.account2]
#apikey =
#secret =

#https://umbrella.cisco.com (Paid-Enterprise)
# The apikey must be an API access token created through the Investigate management UI
#[data_sources.Umbrella]
#[data_sources.Umbrella.Credentials]
#apikey =

#https://urlscan.io (Free)
# URLScan can be used without an API key, but the key allows new submissions to be made
[data_sources.URLScan]
[data_sources.URLScan.Credentials]
apikey = {urlscan}

#https://virustotal.com (Free)
[data_sources.VirusTotal]
ttl = 10080
[data_sources.VirusTotal.Credentials]
apikey = {virustotal}

#https://whoisxmlapi.com (Free)
[data_sources.WhoisXML]
[data_sources.WhoisXML.Credentials]
apikey= {whoisxml}

#https://zetalytics.com (Paid)
#[data_sources.ZETAlytics]
#ttl = 1440
#[data_sources.ZETAlytics.Credentials]
#apikey=

#[data_sources.ZoomEye]
#ttl = 1440
#[data_sources.ZoomEye.Credentials]
#apikey=""")
    fileBuffer.write(fileContents)
    objectBuffer = io.BytesIO(fileBuffer.getvalue().encode())
    # Upload file to S3
    object_name = 'config.ini'
    object_path = 'tools/amass/' + object_name
    status = brevitycore.core.upload_object(objectBuffer,inputBucketName,object_path)
    fileBuffer.close()
    objectBuffer.close()
    return status
    
def generateInstallScriptAmass(inputBucketName):
    # Load AWS access keys for s3 synchronization
    secretName = 'brevity-aws-recon'
    regionName = 'us-east-1'
    secretRetrieved = brevitycore.core.get_secret(secretName,regionName)
    secretjson = json.loads(secretRetrieved)
    awsAccessKeyId = secretjson['AWS_ACCESS_KEY_ID']
    awsSecretKey = secretjson['AWS_SECRET_ACCESS_KEY']
    
    fileBuffer = io.StringIO()
    fileContents = f"""#!/bin/bash

# Create directory structure
export HOME=/root
mkdir $HOME/security
mkdir $HOME/security/tools
mkdir $HOME/security/tools/amass
mkdir $HOME/security/tools/amass/db
mkdir $HOME/security/raw
mkdir $HOME/security/refined
mkdir $HOME/security/curated
mkdir $HOME/security/scope
mkdir $HOME/security/install
mkdir $HOME/security/config
mkdir $HOME/security/run
mkdir $HOME/security/inputs

# Update apt repositories to avoid software installation issues
apt-get update

# Ensure OS and packages are fully upgraded
#apt-get -y upgrade

# Install Git
apt-get install -y git # May already be installed

# Install Python and Pip
apt-get install -y python3 # Likely is already installed
apt-get install -y python3-pip

# Install Golang via cli
apt-get install -y golang

echo 'export GOROOT=/usr/lib/go' >> ~/.bashrc
echo 'export GOPATH=$HOME/go' >> ~/.bashrc
echo 'export PATH=$GOPATH/bin:$GOROOT/bin:$PATH' >> ~/.bashrc
#source ~/.bashrc
    
# Install aws cli
apt-get install -y awscli

# Install docker
curl -fsSL get.docker.com -o get-docker.sh
sh get-docker.sh

# Tool installations

# Install amass for recon
snap install amass

# AWS synchronization of data

# This information will be cleared every session as it is not persistent
export AWS_ACCESS_KEY_ID={awsAccessKeyId}
export AWS_SECRET_ACCESS_KEY={awsSecretKey}
export AWS_DEFAULT_REGION=us-east-1"""
    fileBuffer.write(fileContents)
    objectBuffer = io.BytesIO(fileBuffer.getvalue().encode())

    # Upload file to S3
    object_name = 'bounty-startup-amass.sh'
    object_path = 'config/' + object_name
    bucket = inputBucketName
    installScriptStatus = brevitycore.core.upload_object(objectBuffer,bucket,object_path)
    fileBuffer.close()
    objectBuffer.close()
    return installScriptStatus
