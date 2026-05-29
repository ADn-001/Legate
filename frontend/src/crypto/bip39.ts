import * as bip39 from 'bip39'

export const bip39Module = {
  generatePhrase: (): string[] => {
    const mnemonic = bip39.generateMnemonic(256) // 24 words
    return mnemonic.split(' ')
  },

  validatePhrase: (phrase: string): boolean => {
    return bip39.validateMnemonic(phrase)
  },
}
