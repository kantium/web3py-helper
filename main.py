#!/usr/bin/python3

from web3helper import *

# Config part

configfilepath   = "config.json"
accountfilepath  = "account.json"
accountpassword  = "password"
contractfilepath = "greeter.sol"
compiledsolpath  = "greeter.bin"
compiledfiletx   = "greeter.tx"

# Load configuration file, instanciate the web3 object and finally load the user account

config = Config(configfilepath)
web3 = config.loadWeb3()

# Create a new account
#account = Account(web3).new().save(accountfilepath, accountpassword)

# Load an account
account = Account(web3).load(accountfilepath, accountpassword)

# Print some variables

gasPrice = web3.eth.gasPrice

cprint(levels.low, "Balance    : {} eth".format(account.getBalance()))
cprint(levels.low, "Gas Price  : {} wei".format(gasPrice))
cprint(levels.low, "Syncing... : {}".format(web3.eth.syncing))

# Deploy a contract on the blockchain

#scd = SmartContractDeployer(web3).loadSolidity(contractfilepath)
#scd.compileSol()
#scd.saveCompiledSol(compiledsolpath)
#tr = scd.deploy(account.account.address,["MyArgs"],contractName="<stdin>:greeter", chainId=config.chainId)
#tx = account.launchTransaction(tr)
#scd.saveTx(tx, compiledfiletx)

# Attach the contract

scc = SmartContractCaller(web3, compiledfiletx, compiledsolpath, "<stdin>:greeter")
address = account.account.address
n = web3.eth.getTransactionCount(address)

# Call 2 read only functions of this smart contract (greet and val)

print('Contract value: {}'.format(scc.contractInstance.call().greet()))
print('Contract value: {}'.format(scc.contractInstance.call().val()))

# Call a write function of the smart contract (add) and sign the transaction

prepared_transaction = scc.contractInstance.buildTransaction().add(1)
updated_transaction = scc.updateTransaction(address, prepared_transaction, gas=50000, gasPrice=18000000000)
tx = account.launchTransaction(updated_transaction)
print(tx)

# Create 2 filters

new_block_filter = web3.eth.filter('latest')
new_transaction_filter = web3.eth.filter('pending')

# Every 2 secondes, show filter results

while True:
	time.sleep(2)

	try:
		new_tansaction_changes = web3.eth.getFilterChanges(new_transaction_filter.filter_id)
		new_block_changes = web3.eth.getFilterChanges(new_block_filter.filter_id)
	except:
		cprint(levels.error,"Timeout occurred")
		continue

	if new_tansaction_changes:
		for t in new_tansaction_changes:
			printTransaction(t)

	if new_block_changes:
		for b in new_block_changes:
			printBlock(web3, b, account)
