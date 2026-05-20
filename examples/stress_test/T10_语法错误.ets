
@Component
struct BrokenPage {
  build() {
    Column() {
      Text('Hello'
      // Missing closing parenthesis - syntax error
      Button('Click')
    }
  }
}
