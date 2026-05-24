/**
 * 嵌套组件文件 - 深度 1
 */

import { NestedComponent2 } from './NestedComponentFile2';

@Component
export struct NestedComponent1 {

    build() {
        Column() {
            NestedComponent2()
            NestedComponent2()
            NestedComponent2()
        }
    }

}
