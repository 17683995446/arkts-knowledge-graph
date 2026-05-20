
import { FormHelper } from '../utils/FormHelper'

export class FormService {
  private helper: FormHelper = new FormHelper()
  
  submit(formData: { email: string, phone: string, url: string }): boolean {
    return this.helper.validateEmail(formData.email) &&
           this.helper.validatePhone(formData.phone) &&
           this.helper.validateUrl(formData.url)
  }
}
