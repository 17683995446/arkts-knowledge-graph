
export class Validator {
  static isEmail(value: string): boolean {
    return value.includes('@')
  }
  
  static isPhone(value: string): boolean {
    return /^\d{11}$/.test(value)
  }
  
  static isUrl(value: string): boolean {
    return value.startsWith('http')
  }
}
