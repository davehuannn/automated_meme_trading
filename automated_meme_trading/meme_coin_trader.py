from web3 import Web3
from decouple import config
from eth_account import Account
import json

class MemeCoinTrader:
    SUPPORTED_DEXES = {
        'uniswap_v2': {
            'router': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
            'name': 'Uniswap V2',
            'weth': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
        },
        'sushiswap': {
            'router': '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F',
            'name': 'SushiSwap',
            'weth': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
        },
        'pancakeswap': {
            'router': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
            'name': 'PancakeSwap',
            'weth': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'  # This is WBNB for BSC
        }
    }

    def __init__(self, dex='uniswap_v2', network='ethereum'):
        """
        Initialize the trader with specific DEX and network
        """
        # Set network provider
        if network == 'ethereum':
            self.w3 = Web3(Web3.HTTPProvider(config('INFURA_URL')))
        elif network == 'bsc':
            self.w3 = Web3(Web3.HTTPProvider(config('BSC_NODE_URL')))
        else:
            raise ValueError(f"Unsupported network: {network}")

        # Load private key securely
        self.private_key = config('PRIVATE_KEY')
        self.account = Account.from_key(self.private_key)
        
        # Set DEX configuration
        if dex not in self.SUPPORTED_DEXES:
            raise ValueError(f"Unsupported DEX: {dex}")
        
        self.current_dex = dex
        self.router_address = Web3.to_checksum_address(self.SUPPORTED_DEXES[dex]['router'])
        self.weth_address = Web3.to_checksum_address(self.SUPPORTED_DEXES[dex]['weth'])
        
        # Load router ABI
        abi_filename = f"{dex}_router_abi.json"
        with open(abi_filename, 'r') as f:
            self.router_abi = json.load(f)
        
        self.router_contract = self.w3.eth.contract(
            address=self.router_address,
            abi=self.router_abi
        )

    def get_token_price(self, token_address, amount=1):
        """
        Get token price in ETH
        """
        token_address = Web3.to_checksum_address(token_address)
        
        try:
            # Get amounts out for 1 token
            amounts = self.router_contract.functions.getAmountsOut(
                Web3.to_wei(amount, 'ether'),
                [token_address, self.weth_address]
            ).call()
            
            return Web3.from_wei(amounts[1], 'ether')
        except Exception as e:
            print(f"Error getting price: {str(e)}")
            return None

    def buy_token(self, token_address, amount_eth):
        """
        Buy meme tokens with ETH
        """
        token_address = Web3.to_checksum_address(token_address)
        
        # Calculate deadline for transaction
        deadline = self.w3.eth.get_block('latest').timestamp + 300  # 5 minutes
        
        # Get the swap path (ETH -> Token)
        path = [
            Web3.to_checksum_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),  # WETH
            token_address
        ]
        
        # Prepare the transaction
        transaction = self.router_contract.functions.swapExactETHForTokens(
            0,  # Minimum tokens to receive (set to 0 for testing)
            path,
            self.account.address,
            deadline
        ).build_transaction({
            'from': self.account.address,
            'value': Web3.to_wei(amount_eth, 'ether'),
            'gas': 250000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # Sign and send the transaction
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def sell_token(self, token_address, amount_tokens):
        """
        Sell meme tokens for ETH
        """
        token_address = Web3.to_checksum_address(token_address)
        
        # Calculate deadline for transaction
        deadline = self.w3.eth.get_block('latest').timestamp + 300  # 5 minutes
        
        # Get the swap path (Token -> ETH)
        path = [
            token_address,
            Web3.to_checksum_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')  # WETH
        ]
        
        # Prepare the transaction
        transaction = self.router_contract.functions.swapExactTokensForETH(
            amount_tokens,
            0,  # Minimum ETH to receive (set to 0 for testing)
            path,
            self.account.address,
            deadline
        ).build_transaction({
            'from': self.account.address,
            'gas': 250000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # Sign and send the transaction
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def approve_token(self, token_address):
        """
        Approve the router to spend tokens
        """
        token_address = Web3.to_checksum_address(token_address)
        
        # Load ERC20 ABI
        with open('erc20_abi.json', 'r') as f:
            erc20_abi = json.load(f)
        
        token_contract = self.w3.eth.contract(
            address=token_address,
            abi=erc20_abi
        )
        
        # Prepare approval transaction
        transaction = token_contract.functions.approve(
            self.router_address,
            2**256 - 1  # Maximum approval
        ).build_transaction({
            'from': self.account.address,
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # Sign and send the transaction
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return self.w3.eth.wait_for_transaction_receipt(tx_hash) 