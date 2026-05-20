
import { Validator } from './Validator'

export class FormHelper {
  validateEmail(email: string): boolean {
    return Validator.isEmail(email)
  }
  
  validatePhone(phone: string): boolean {
    return Validator.isPhone(phone)
  }
  
  validateUrl(url: string): boolean {
    return Validator.isUrl(url)
  }
}
