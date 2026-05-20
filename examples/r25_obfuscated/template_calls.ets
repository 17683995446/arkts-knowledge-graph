
class TemplateCalls {
  private data: string = 'test'
  
  format(): string {
    return `${this.data} - ${this.getValue()}`
  }
  
  private getValue(): string {
    return 'value'
  }
  
  multiLine(): string {
    return `
      ${this.format()}
      ${this.data}
    `
  }
}
