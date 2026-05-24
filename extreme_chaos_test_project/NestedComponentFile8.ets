/**
 * 嵌套组件文件 - 深度 8
 */

import { NestedComponent9 } from './NestedComponentFile9';

@Component
export struct NestedComponent8 {

    build() {
        Column() {
            NestedComponent9()
            NestedComponent9()
            NestedComponent9()
        }
    }

}
