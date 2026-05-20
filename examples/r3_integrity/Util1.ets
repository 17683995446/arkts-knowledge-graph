
class Util1 {
  format(input: string): string {
    return this.trim(input)
  }

  private trim(s: string): string {
    return s.trim()
  }

  parse(input: string): object {
    return JSON.parse(input)
  }
}
