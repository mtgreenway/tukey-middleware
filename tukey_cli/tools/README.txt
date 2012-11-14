addTukeyUser.py talks to the postgres db to modify users

cloudTools.py, compute.py and storage.py talk to Eucalyptus using libcloud<http://libcloud.apache.org/>


To use addTukeyUser.py pass the username as the argument as the following examples demonstrate:

# add user with username test
./addTukeyUser test

# add user with username test and Shibboleth eppn test@test.test
./addTukeyUser -s test@test.test test

# add Shibboleth eppn to existing user test
./addTukeyUser -e -s test@test.test test

# delete user test
./addTukeyUser -d test
