"""
    Web3py beta 4 helper module
    18.01.2018
    Stéphane Küng
"""

import os
import time
import json
import socket
import requests
import datetime
from decimal import Decimal
from solc import compile_source
from web3 import Web3, HTTPProvider


class Config:
    """Web3 factory configurator based on configuration file"""

    filename = None
    config = None
    chainId = None

    def __init__(self, filename):
        self.filename = filename
        if not os.path.isfile(filename):
            raise Exception("File doesn't exist")

        with open(filename) as infile:
            self.config = json.load(infile)

        self.chainId = self.config["chainId"]

    def loadWeb3(self):
        """Load HTTP Provider from URL"""
        return Web3(HTTPProvider(self.config["endpoint"]))

    # TODO: Can be deducted from web3
    def getChainId(self):
        return self.config["chainId"]


class Rates:
    """Used to get the exchange rate USD / ETH"""

    # TODO: To be moved in config file
    apiUrl = "https://api.coinmarketcap.com/v1/ticker/ethereum"
    data = None
    usd = None

    def __init__(self):
        self.update()

    def __str__(self):
        return "Unset" if not self.account else self.account.address

    def update(self):
        self.data = requests.get(self.apiUrl).json()[0]
        self.usd = Decimal(self.data['price_usd'])

    def ethToUsd(self, eth):
        """convert ETH value to USD"""
        return self.usd * eth

    def usdToEth(self, usd):
        """Convert USD currency to ETH"""
        return (1.00/float(self.usd)) * usd


class Account:
    """Handle an account (private and public key) to sign and publish transaction
       on the blockchain
    """

    web3 = None
    account = None

    def __init__(self, web3):
        self.web3 = web3

    def __str__(self):
        return "Unset" if not self.account else self.account.address

    def load(self, filename, password):
        """Load a password protected account file"""

        if self.account:
            raise Exception("Account already set")

        if not os.path.isfile(filename):
            raise Exception("File doesn't exist")

        with open(filename) as infile:
            acct_enc = json.load(infile)

        acct_un = self.web3.eth.account.decrypt(acct_enc, password)
        acct = self.web3.eth.account.privateKeyToAccount(acct_un)

        self.account = acct
        cprint(levels.low, "Account loaded")
        return self

    def save(self, filename, password):
        """Save current account to a password encrypted file"""

        if os.path.isfile(filename):
            raise Exception("A file already exist here")

        acct_enc = self.web3.eth.account.encrypt(self.account.privateKey, password)

        with open(filename, 'w') as outfile:
            json.dump(acct_enc, outfile, sort_keys = True, indent = 4, ensure_ascii = False)

        cprint(levels.low, "Account saved")
        return self

    def new(self):
        """Generate a new local account with private key"""

        if self.account:
            raise Exception("Account already set")

        self.account = self.web3.eth.account.create(os.urandom(20))
        cprint(levels.low, "Account randomnly generated")
        return self

    def getBalance(self):
        """Get the current account balance"""

        if self.account:
            wei = self.web3.eth.getBalance(self.account.address)
            return self.web3.fromWei(wei, 'ether')
        else:
            raise Exception("No account set")

    def _acceptTransaction(self, transaction):
        """Print a tansaction warning to the user. To be used before signing a transaction"""
        cprint(levels.low, "Transaction : {}".format(transaction))
        total = transaction["gas"]*transaction["gasPrice"]
        r = Rates()
        usd = r.ethToUsd(self.web3.fromWei(total, 'ether'))
        ether = self.web3.fromWei(total, 'ether')
        cprint(levels.warning, "Transaction : {}".format("Gas : {0}\nGas price : {1} wei\nTotal : {2} Ether ({3} USD)".format(transaction["gas"],transaction["gasPrice"],ether,usd)))

        while True:
            cprint(levels.warning, "Do you accept to sign that fees ? [Y/N]")
            answer = input()
            if "n" == answer.lower():
                cprint(levels.low, "Transaction aborted")
                raise Exception("Transaction aborted")
            elif "y" == answer.lower():
                break
        cprint(levels.low, "Transaction accepted")
        return True

    def launchTransaction(self, transaction, override=False):
        """Sign and publish a transaction with user permission"""

        if override or self._acceptTransaction(transaction):
            signed = self.account.signTransaction(transaction)
            cprint(levels.low, "Transaction signed")
            tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
            cprint(levels.success, "Transaction sent ({})".format(self.web3.toHex(tx_hash)))
            return self.web3.toHex(tx_hash)

    def sendTo(self, to, amount, chainId):
        """Send an amount of ether (in wei) to an address"""
        transaction = {
            'nonce': self.web3.eth.getTransactionCount(self.account.address),
            'from': self.account.address,
            'gas': 21000,
            'gasPrice': self.web3.eth.gasPrice,
            'chainId': chainId,
            'value': amount,
            'data': '',
            'to':to
        }
        return self.launchTransaction(transaction)


class SmartContractCaller:
    """Allow calling function on a published smart contract"""

    contractInstance = None
    tx_receipt = None
    address = None

    def __init__(self, web3, tx_filename, bin_filename, contractName):
        """Re-link a Smart Contract based on the transaction hash and the compiled source"""

        self.web3 = web3
        cprint(levels.low, "loading smart contract...")

        if not os.path.isfile(tx_filename):
            raise Exception("TX File not found")

        if not os.path.isfile(bin_filename):
            raise Exception("Compiled Sol File not found")

        with open(tx_filename) as infile:
            self.tx_hash = json.load(infile)
            cprint(levels.low, "tx_filename loaded ({0})".format(self.tx_hash))

        with open(bin_filename) as infile:
            self.compiledSol = json.load(infile)
            cprint(levels.low, "bin_filename loaded")

        self.tx_receipt = self.web3.eth.getTransactionReceipt(self.tx_hash)
        cprint(levels.low, "tx_receipt {0}".format(self.tx_receipt))
        if not self.tx_receipt:
            raise Exception("tx_receipt still Null...")

        self.address = self.tx_receipt['contractAddress']
        MyContract = self.web3.eth.contract(
            abi = self.compiledSol[contractName]['abi'],
            #address = contract_address,
            bytecode = self.compiledSol[contractName]['bin'],   # The keyword `code` has been deprecated.  You should use `bytecode` instead.
            bytecode_runtime = self.compiledSol[contractName]['bin-runtime'],  # the keyword `code_runtime` has been deprecated.  You should use `bytecode_runtime` instead.
        )
        self.contractInstance = MyContract(self.address)

    def updateTransaction(self, address, transaction, nonce=None, gas=None, gasPrice=None):
        """Add all missing information to the generated transaction"""
        chainId = transaction.pop('chainId', None)
        if not nonce:
            transaction["nonce"] = self.web3.eth.getTransactionCount(address)
        else:
            transaction["nonce"] = nonce
        transaction["from"] = address

        if not gasPrice:
            gasPrice = self.web3.eth.gasPrice
            cprint(levels.info, "No gasPrice specified. GasPrice set to {}".format(gasPrice))
        transaction["gasPrice"] = gasPrice

        if not gas:
            gas = self.web3.eth.estimateGas(transaction)
            cprint(levels.info, "No gas specified. Based on transaction estimation is {0}, gas set to {1}".format(gas, gas * 2))
            gas += gas

        transaction["gas"] = gas
        transaction["chainId"] = chainId

        return transaction


class SmartContractDeployer:
    """Can compile and deploy a smart contract on the blockchain"""

    web3 = None
    sourceSol = None
    compiledSol = None
    tx_hash = None

    def __init__(self, web3):
        self.web3 = web3

    def loadSolidity(self, filename):
        """Load source code (.sol) file"""
        with open(filename) as f:
            self.sourceSol = f.read()

        cprint(levels.low, "Solidity code loaded")
        return self

    def compileSol(self):
        """Compile source code"""
        if not self.sourceSol:
            raise Exception("No source code loaded")

        self.compiledSol = compile_source(self.sourceSol)
        cprint(levels.low, "Solidity code compiled")

    def saveCompiledSol(self, filename):
        """Save the compiled source code"""
        with open(filename, 'w') as outfile:
            json.dump(self.compiledSol, outfile, sort_keys = True, indent = 4, ensure_ascii = False)

        cprint(levels.low, "Compiled code saved")

    def saveTx(self, tx_hash, filename):
        """When a smart contract is published, a transaction hash is generated,
           it must be saved using this method in order to re-ling with the smart contract later
        """
        self.tx_hash = tx_hash
        with open(filename, 'w') as outfile:
            json.dump(self.tx_hash, outfile, sort_keys = True, indent = 4, ensure_ascii = False)

        cprint(levels.low, "Transaction hash saved")

    # TODO: function must be rename, content cleaned
    def deploy(self, address, args, contractName, chainId, gas=None, gasPrice=None,gasMultiplicator=4):
        """Return the Smart Contract publication Transaction"""
        contract = self.web3.eth.contract(abi=self.compiledSol[contractName]['abi'], bytecode=self.compiledSol[contractName]['bin'])
        data = contract._encode_constructor_data(args)

        transaction = {
            'nonce': self.web3.eth.getTransactionCount(address),
            'from': address,
            #'gas': gas,
            #'gasPrice': gasPrice,
            #'chainId': 42,
            'value': 0,
            'data': data, #+data[2:]*10,
            'to':address
        }

        if not gasPrice:
            gasPrice = self.web3.eth.gasPrice
            cprint(levels.info, "No gasPrice specified. GasPrice set to {}".format(gasPrice))
        transaction["gasPrice"] = gasPrice

        if not gas:
            gas = self.web3.eth.estimateGas(transaction)
            cprint(levels.info, "No gas specified. Based on transaction estimation is {0}, gas set to {1}".format(gas, gas * gasMultiplicator))
            gas = gas * gasMultiplicator

        transaction["gas"] = gas
        transaction["to"] = ''
        transaction["chainId"] = chainId

        return transaction


class levels:
    """Used to get some colors in the terminal"""

    reset = "\x1b[0m"
    danger = "\x1b[1;38;5;{0}m".format(196)
    error = "\x1b[38;5;{0}m".format(196)
    warning = "\x1b[38;5;{0}m".format(208)
    success = "\x1b[38;5;{0}m".format(154)
    info = "\x1b[38;5;{0}m".format(39)
    normal = "\x1b[38;5;{0}m".format(27)
    surprise = "\x1b[38;5;{0}m".format(207)
    low = "\x1b[38;5;{0}m".format(244)
    yellow = "\x1b[38;5;{0}m".format(226)


def cprint(color, msg):
    """Color printing function"""

    t = str(datetime.datetime.now().strftime("%H:%M:%S"))
    print("{}".format(color + t + "    " + msg + levels.reset))


def printTransaction(web3, tx_hash):
    """print a transaction in the terminal"""

    try:
        transaction = web3.eth.getTransaction(tx_hash)
        cprint(levels.low, "Transaction from {0} to {1}".format(transaction["from"],transaction["to"]))
    except:
        cprint(levels.error,"Timeout occurred")

def printBlock(web3, block_hash, account=None):
    """Print a block with all related transactions"""

    block = web3.eth.getBlock(block_hash)
    symb0 = "─" if len(block["transactions"]) == 0 else "┬"
    cprint(levels.success, "├─{0} Block {1}, {2} Transaction(s), Hash {3}".format(symb0, block["number"], len(block["transactions"]), web3.toHex(block["hash"])))

    if block["transactions"]:
        for tx_hash in block["transactions"]:

            symb1 = "└─" if tx_hash == block["transactions"][-1] else "├─"
            symb2 = " " if tx_hash == block["transactions"][-1] else "│"

            transaction = web3.eth.getTransaction(tx_hash)
            lcolor = levels.warning if transaction["from"] == account.account.address or transaction["to"] == account.account.address else levels.low

            cprint(lcolor, "│ {0}┬─ Transaction from {1} to {2}".format(symb1,transaction["from"],transaction["to"]))			
            cprint(lcolor, "│ {0} └─  Value {1}, Gas {2}, GasPrice {3}".format(symb2, transaction["value"], transaction["gas"], transaction["gasPrice"],))		


