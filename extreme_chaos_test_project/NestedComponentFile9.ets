/**
 * 嵌套组件文件 - 深度 9
 */

import { NestedComponent10 } from './NestedComponentFile10';

@Component
export struct NestedComponent9 {

    build() {
        Column() {
            NestedComponent10()
            NestedComponent10()
            NestedComponent10()
        }
    }

}
