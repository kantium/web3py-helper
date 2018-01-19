pragma solidity ^0.4.19;
contract mortal {
    /* Define variable owner of the type address */
    address owner;

    /* This function is executed at initialization and sets the owner of the contract */
    function mortal() public { owner = msg.sender; }

    /* Function to recover the funds on the contract */
    function kill() public { if (msg.sender == owner) selfdestruct(owner); }
}

contract greeter is mortal {
    string public greeting;
    int8 public val = 0;
    
    function greeter(string _greeting) public {
        greeting = _greeting;
    }
    
    function add(int8 i) public {
        val += i;
    }

    function greet() public constant returns (string) {
        return greeting;
    }
}