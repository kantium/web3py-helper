# web3py-helper

Helper module for web3py beta 4

## Documentation

The main python file shows some examples on how to use the helper, it is very similar to the following documentation

### Account

This is how you can generate a local encrypted new account, save it locally and load it
```
account = Account(web3).new().save(accountfilepath, accountpassword)
account = Account(web3).load(accountfilepath, accountpassword)
```

Send money from the current local account to an address
`account.sendTo(to, wei, config.chainId)`

### Deploy a smart contract

How to deploy a smart contract on the block chain
```
scd = SmartContractDeployer(web3).loadSolidity(contractfilepath)
scd.compileSol()
scd.saveCompiledSol(compiledsolpath)
tr = scd.deploy(account.account.address,["MyArgs"],contractName="<stdin>:greeter", chainId=config.chainId)
tx = account.launchTransaction(tr)
scd.saveTx(tx, compiledfiletx)
```

Users have to manually validate every transaction is gonna sign for
![Approuve a transaction](https://raw.githubusercontent.com/kantium/web3py-helper/master/signature.png)

### Call methods on smart contract

You need to re-ling to your published smart contract with the compiled smart contract and a transaction hash
```
scc = SmartContractCaller(web3, compiledfiletx, compiledsolpath, "<stdin>:greeter")
address = account.account.address
n = web3.eth.getTransactionCount(address)
```

To read a function or value/state directly on the Ethereum node
`print('Contract value: {}'.format(scc.contractInstance.call().greet()))`

To use a function that will cost gas
```
prepared_transaction = scc.contractInstance.buildTransaction().add(1)
updated_transaction = scc.updateTransaction(address, prepared_transaction, gas=50000, gasPrice=18000000000)
tx = account.launchTransaction(updated_transaction)
```

### Color Printing

Some pretty printing functions (for block and transaction) can be used on filters, for example :
![Filter](https://raw.githubusercontent.com/kantium/web3py-helper/master/filter.png)

## Todo

- [X] Code
- [X] Basic documentation
- [ ] Clean the code
- [ ] Renaming methods
- [ ] Refactoring 
- [ ] Add checks
- [ ] Import ChainId from web3, not from config

## Issues

This issue is not related to my code, but can occur if using a Clique consensus POA (tested on an Azure private Ethereum Consortium).
In this case `extraData` contain more information than expected:

```
File "/usr/local/lib/python3.5/dist-packages/web3-4.0.0b5-py3.5.egg/web3/middleware/pythonic.py", line 94, in to_hexbytes
    result, len(result), num_bytes
ValueError: The value HexBytes('0x...') is 97 bytes, but should be 32
```

Just edit `pythonic.py` and modify the following code :

```
line  80:  def to_hexbytes(num_bytes, val, variable_length=False, override=True):
...
line  91:    else:
line  92:      if override:
line  93:        return result
line  94:      else:
line  95:        raise ValueError(
...
line 169:    'extraData': to_hexbytes(32, variable_length=True),
```

