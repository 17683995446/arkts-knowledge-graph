/**
 * 嵌套组件文件 - 深度 20
 */

import { NestedComponent21 } from './NestedComponentFile21';

@Component
export struct NestedComponent20 {

    build() {
        Column() {
            NestedComponent21()
            NestedComponent21()
            NestedComponent21()
        }
    }

}
